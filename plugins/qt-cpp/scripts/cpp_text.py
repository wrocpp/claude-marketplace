"""Text helpers for the model lint: masking, path tests, project config, and what may be shown to Claude.

The lint reads text, not compiler state. It never runs a compiler and never imports a project.
"""
import json
import os
import pathlib
import re

CPP_SUFFIXES = {".cpp", ".cc", ".cxx", ".c++", ".hpp", ".hh", ".hxx", ".h++", ".h", ".ipp", ".inl", ".tpp", ".cppm", ".ixx"}
CONFIG_RELATIVE = pathlib.Path(".claude") / "qt-cpp.json"
MARKER_REASON = re.compile(r"[A-Za-z0-9_]")
MAX_CONFIG_BYTES = 65536

# What mask() blanks, tried left to right: a raw string, a comment, a string, a character literal (an apostrophe
# after a digit or a hex letter is a digit separator, as in 1'000), and, on request, a preprocessor line.
LITERALS = (
    r'R"(?P<delim>[^()\\\s]{0,16})\((?s:.*?)\)(?P=delim)"',
    r"//[^\n]*",
    r"/\*(?s:.*?)(?:\*/|\Z)",
    r'"(?:\\.|[^"\\\n])*"?',
    r"(?<![0-9A-Fa-f])'(?:\\.|[^'\\\n])*'?",
)
PREPROCESSOR = r"(?m:^[ \t]*#(?:\\\n|[^\n])*)"
MASK_KEEPING_PREPROCESSOR = re.compile("|".join(LITERALS))
MASK_DROPPING_PREPROCESSOR = re.compile("|".join((PREPROCESSOR,) + LITERALS))


class Finding:
    def __init__(self, line, rule, message):
        self.line = line
        self.rule = rule
        self.message = message

    def render(self, path=""):
        where = f"{path}:{self.line}" if path else f"line {self.line}"
        return f"{where}: [{self.rule}] {self.message}"

    def __repr__(self):
        return f"Finding({self.line}, {self.rule!r})"


def is_cpp_path(path):
    return pathlib.PurePath(path).suffix.lower() in CPP_SUFFIXES


def _blank(found):
    return "".join(c if c == "\n" else " " for c in found.group(0))


def mask(text, drop_preprocessor=False):
    """Blank comments, string and character literals (and, on request, preprocessor lines).

    Length and newlines are preserved, so offsets and line numbers still match the input.
    """
    pattern = MASK_DROPPING_PREPROCESSOR if drop_preprocessor else MASK_KEEPING_PREPROCESSOR
    return pattern.sub(_blank, text)


def line_of(text, offset):
    return text.count("\n", 0, offset) + 1


def has_marker(lines, line_number, marker):
    """True when line_number or the line before carries `marker: <reason>` with a non-empty reason."""
    pattern = re.compile(re.escape(marker) + r"\s*:\s*(\S.*)")
    for number in (line_number, line_number - 1):
        if 1 <= number <= len(lines):
            found = pattern.search(lines[number - 1])
            if found and MARKER_REASON.search(found.group(1)):
                return True
    return False


def read_config(path):
    """(config, readable) for one config file."""
    try:
        if path.stat().st_size > MAX_CONFIG_BYTES:
            return None, False
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None, False
    return (loaded, True) if isinstance(loaded, dict) else (None, False)


def config_candidates(start_dirs):
    seen = set()
    for start in start_dirs:
        if not isinstance(start, (str, os.PathLike)) or not start:
            continue
        directory = pathlib.Path(start).resolve()
        for candidate in (directory, *directory.parents):
            if candidate in seen:
                break
            seen.add(candidate)
            yield candidate / CONFIG_RELATIVE


def find_config(start_dirs):
    """Return (config, readable). A missing file is (None, True); a malformed one is (None, False)."""
    for config in config_candidates(start_dirs):
        if config.is_file():
            return read_config(config)
    return None, True


PATH_TEXT = re.compile(r"[A-Za-z0-9_./-]{1,128}")
RULE_FLAGS = ("block", "disable")
RULES = ("begin-end-pairing", "dependent-base-connect", "row-as-key", "fromvalue-in-template-emit")


def safe_path(text, fallback="the file"):
    ok = PATH_TEXT.fullmatch(text) and not text.startswith("/") and ".." not in text.split("/")
    return text if ok else fallback


def rule_flags(rule, section):
    """(flags, wrong_keys) of one rule's section. Only booleans survive; the key names are the fixed vocabulary."""
    if not isinstance(section, dict):
        return {}, [rule]
    flags = {flag: section[flag] for flag in RULE_FLAGS if isinstance(section.get(flag), bool)}
    return flags, [f"{rule}.{flag}" for flag in RULE_FLAGS if flag in section and flag not in flags]


def validate_config(raw):
    """Return (config, wrong_keys). Only booleans survive.

    wrong_keys names are drawn from the fixed vocabulary above, never from the file.
    """
    clean = {rule: {} for rule in RULES}
    wrong = []
    for rule in RULES:
        section = raw.get(rule) if isinstance(raw, dict) else None
        if section is not None:
            clean[rule], bad = rule_flags(rule, section)
            wrong.extend(bad)
    return clean, wrong


def env_off():
    return os.environ.get("QT_CPP_OFF") == "1"
