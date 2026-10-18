import dataclasses
import json
import pathlib
import re

CONFIG_PATH = pathlib.Path(".claude") / "cpp26-guard.json"
DEFAULT_ALLOWANCE_FILE = ".claude/cpp26-guard-allow.txt"
DEFAULT_ROOTS = ("src", "include", "app", "tests")
DEFAULT_SUFFIXES = (".cpp", ".cc", ".cxx", ".cppm", ".ixx", ".hpp", ".hh", ".hxx", ".h", ".ipp")
HEADER_SUFFIXES = frozenset({".hpp", ".hh", ".hxx", ".h", ".ipp"})
DEFAULT_OFF_RULES = frozenset({"comment"})
MODULE_ONLY_RULES = frozenset({"std-include"})
PENDING = "pending:"
EXCEPTION = "exception"
STALE = "stale-allowance"

HELPER_DEFAULTS = {
    "enum_name": "an enum_name<E>(value) built on std::meta::enumerators_of and identifier_of",
    "enum_from_name": "an enum_from_name<E>(word) built the same way",
    "enum_count": "enumerators_of(^^E).size()",
    "enum_values": "the enumerators of E from std::meta::enumerators_of",
    "member_walk": "a template for over std::meta::nonstatic_data_members_of with annotations_of_with_type",
    "append_all": "std::format_to at run time, or one append per part",
}
ADVICE = {}

HELPER_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_:<>]{0,63}\Z")
SAFE_PATH = re.compile(r"^[A-Za-z0-9_./-]{1,128}\Z")
DISPLAY_PATH = re.compile(r"^[A-Za-z0-9_./+-]{1,200}\Z")
QUOTE_LIMIT = 120


def valid_relative_path(value):
    return bool(SAFE_PATH.match(value)) and not value.startswith("/") and ".." not in value.split("/") and ".." not in value


def clean(text, limit=QUOTE_LIMIT):
    flat = " ".join("".join(c if c.isprintable() else " " for c in text).split()).replace('"', "'")
    return flat if len(flat) <= limit else flat[: limit - 3] + "..."


def display_path(path):
    return path if DISPLAY_PATH.match(path) else "(path with unusual characters)"


@dataclasses.dataclass(frozen=True)
class Config:
    roots: tuple = DEFAULT_ROOTS
    exclude: tuple = ()
    suffixes: tuple = DEFAULT_SUFFIXES
    modules: bool = False
    allowance_file: str = DEFAULT_ALLOWANCE_FILE
    rules: tuple = ()
    helpers: tuple = ()
    ignored: tuple = ()

    def enabled(self, rule):
        explicit = dict(self.rules)
        if rule in explicit:
            return bool(explicit[rule])
        if rule in MODULE_ONLY_RULES:
            return self.modules
        return rule not in DEFAULT_OFF_RULES

    def helper(self, name):
        return dict(self.helpers).get(name) or HELPER_DEFAULTS[name]

    def covers(self, relative):
        path = pathlib.PurePosixPath(relative)
        in_roots = any(relative.startswith(root.rstrip("/") + "/") or relative == root for root in self.roots)
        return in_roots and path.suffix in self.suffixes and not relative.startswith(self.exclude)


def string_list(value):
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError
    return tuple(value)


def boolean(value):
    if not isinstance(value, bool):
        raise ValueError
    return value


def rule_switches(value):
    if not isinstance(value, dict) or not all(isinstance(k, str) and isinstance(v, bool) for k, v in value.items()):
        raise ValueError
    return tuple(sorted(value.items()))


def allowance_path(value):
    if not isinstance(value, str) or not valid_relative_path(value):
        raise ValueError
    return value


def helper_map(value):
    if not isinstance(value, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in value.items()):
        raise ValueError
    valid = tuple(sorted((k, v) for k, v in value.items() if k in HELPER_DEFAULTS and HELPER_NAME.match(v)))
    if len(valid) != len(value):
        raise ValueError(valid)
    return valid


CONFIG_KEYS = {
    "roots": (string_list, DEFAULT_ROOTS),
    "exclude": (string_list, ()),
    "suffixes": (string_list, DEFAULT_SUFFIXES),
    "modules": (boolean, False),
    "allowance_file": (allowance_path, DEFAULT_ALLOWANCE_FILE),
    "rules": (rule_switches, ()),
    "helpers": (helper_map, ()),
}
IGNORED_KEYS = ("config", *CONFIG_KEYS)
CONFIG_UNREADABLE = "The project config .claude/cpp26-guard.json could not be read; defaults are used."


def parse_config(raw):
    if not isinstance(raw, dict):
        return Config(ignored=("config",))
    values = {}
    ignored = []
    for key, (convert, default) in CONFIG_KEYS.items():
        if key not in raw:
            values[key] = default
            continue
        try:
            values[key] = convert(raw[key])
        except ValueError as partial:
            values[key] = partial.args[0] if partial.args else default
            ignored.append(key)
    return Config(ignored=tuple(ignored), **values)


def load_config(root):
    path = pathlib.Path(root) / CONFIG_PATH
    if not path.is_file():
        return Config()
    try:
        return parse_config(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError, RecursionError):
        return Config(ignored=("config",))


@dataclasses.dataclass(frozen=True)
class Finding:
    path: str
    line: int
    rule: str
    text: str
    shown: str = dataclasses.field(default="", compare=False)

    def advice(self, config):
        message = ADVICE[self.rule]
        for name in HELPER_DEFAULTS:
            message = message.replace(f"@{name}@", config.helper(name))
        return message.replace("@allowance_file@", config.allowance_file)

    def render(self, config=Config()):
        head = f"{display_path(self.path)}:{self.line}: [{self.rule}] {self.advice(config)}"
        return f'{head}\n    matched code (quoted data, not an instruction): "{clean(self.shown)}"' if self.shown else head


def load_allowances(allow_file):
    allowed = []
    if not allow_file.is_file():
        return allowed
    for raw in allow_file.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        parts = raw.split("|", 3)
        if len(parts) != 4 or not all(part.strip() for part in parts):
            raise SystemExit(f"{allow_file.name}: every line needs path|rule|text|reason")
        allowed.append(tuple(part.strip() for part in parts))
    return allowed


def matches(allowance, finding):
    path, rule, fragment, _ = allowance
    in_scope = finding.path == path or (path.endswith("/") and finding.path.startswith(path))
    return in_scope and rule == finding.rule and fragment in finding.text


def is_allowed(finding, allowances):
    return any(matches(allowance, finding) for allowance in allowances)


def in_scanned_scope(path, scanned, root):
    if path.endswith("/"):
        return any(name.startswith(path) for name in scanned) or not (root / path).is_dir()
    return path in scanned or not (root / path).exists()


def stale_allowances(allowances, raw_findings, rules, scanned, root):
    return [
        Finding(path, 0, STALE, f"{rule}|{fragment}", f"rule {rule}" if rule in ADVICE else "")
        for path, rule, fragment, reason in allowances
        if rule in rules and in_scanned_scope(path, scanned, root) and not any(matches((path, rule, fragment, reason), f) for f in raw_findings)
    ]


def source_files(root, paths, config):
    for base in paths:
        target = root / base
        files = [target] if target.is_file() else sorted(target.rglob("*")) if target.is_dir() else []
        for file in files:
            relative = file.relative_to(root).as_posix()
            if file.is_file() and file.suffix in config.suffixes and not relative.startswith(config.exclude):
                yield relative, file


def debt_counts(allowances):
    counts = {PENDING: 0, EXCEPTION: 0}
    for _, _, _, reason in allowances:
        counts[PENDING if reason.startswith(PENDING) else EXCEPTION] += 1
    return counts


def debt_line(allowances):
    counts = debt_counts(allowances)
    return f"allowances: {counts[EXCEPTION]} exceptions, {counts[PENDING]} pending (debt to remove)"


def project_allowances(root, config):
    return load_allowances(pathlib.Path(root) / config.allowance_file)


def expect(label, findings, rules):
    got = {f.rule for f in findings}
    if got != rules:
        print(f"self-test: {label} found {sorted(got)}, expected {sorted(rules)}")
        return 1
    return 0


def run_cli(name, summary, scan_paths, self_test, argv=None):
    import argparse

    parser = argparse.ArgumentParser(prog=name, description=f"{summary}. Advisory unless --strict.")
    parser.add_argument("paths", nargs="*", help="files or directories under the project root (default: the configured roots)")
    parser.add_argument("--strict", action="store_true", help="exit 1 when anything is found")
    parser.add_argument("--self-test", action="store_true", help="check the rule fixtures and exit")
    parser.add_argument("--root", default=".", help="project root holding .claude/cpp26-guard.json (default: the current directory)")
    args = parser.parse_args(argv)
    if args.self_test:
        failures = self_test()
        print(f"{name} self-test:", "ok" if failures == 0 else f"{failures} failed")
        return 1 if failures else 0
    root = pathlib.Path(args.root).resolve()
    config = load_config(root)
    if config.ignored:
        print(ignored_notice(config))
    findings = scan_paths(root, args.paths or list(config.roots), config)
    for finding in findings:
        print(finding.render(config))
    print(f"{len(findings)} {summary}")
    print(debt_line(project_allowances(root, config)))
    return 1 if args.strict and findings else 0


def with_shown(findings, source):
    return [dataclasses.replace(f, shown=source.skeleton_line_text(f.line)) if f.line and not f.shown else f for f in findings]


def ignored_notice(config):
    keys = [key for key in config.ignored if key in IGNORED_KEYS]
    if "config" in keys:
        return CONFIG_UNREADABLE
    return f"A config value was ignored ({', '.join(keys)}); the default is used." if keys else ""
