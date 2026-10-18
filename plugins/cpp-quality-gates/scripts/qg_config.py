"""Reads .claude/cpp-quality-gates.json. The file belongs to the project, so it is untrusted.

Every value that reaches a command line or a path is validated by type first. An invalid value
is refused: the script exits 2 and the message names the setting (section.key), never its
content. Commands are never run through a shell: a configured command is split into an argument
list and refused if it contains a shell metacharacter.
"""
import json
import os
import pathlib
import re
import shlex
import sys

CONFIG_PATH = pathlib.Path(".claude/cpp-quality-gates.json")
# The first character is never "-": a value that becomes an argument must not parse as an option.
PATH_PATTERN = re.compile(r"[A-Za-z0-9_.][A-Za-z0-9_./-]{0,127}")
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_.][A-Za-z0-9_.+-]{0,63}")
SUFFIX_PATTERN = re.compile(r"\.[A-Za-z0-9]{1,8}")
NAME_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_:<>]{0,63}")
SHELL_METACHARACTERS = frozenset(";|&$`<>()\\\n\r")
QUOTE_LIMIT = 120
COMMAND_LIMIT = 512
MAX_CRAP_LIMIT = 1000
INT_LIMIT = 10_000_000
SECONDS_LIMIT = 86_400
MISSING = object()


def refuse(label):
    print(f"cpp-quality-gates: invalid value for {label}; refused", file=sys.stderr)
    raise SystemExit(2)


def load(path=None):
    path = pathlib.Path(path) if path else CONFIG_PATH
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        refuse("the config file")
    if not isinstance(data, dict):
        refuse("the config file")
    return data


def is_path(value):
    return isinstance(value, str) and bool(PATH_PATTERN.fullmatch(value)) and ".." not in value.split("/") and not value.startswith("/")


def is_token(value):
    return isinstance(value, str) and bool(TOKEN_PATTERN.fullmatch(value))


def is_name(value):
    return isinstance(value, str) and bool(NAME_PATTERN.fullmatch(value))


def is_int(value, low=0, high=INT_LIMIT):
    return isinstance(value, int) and not isinstance(value, bool) and low <= value <= high


def is_free_text(value):
    return isinstance(value, str) and 0 < len(value) <= QUOTE_LIMIT and value.isprintable()


CHECKS = {
    "path": is_path,
    "token": is_token,
    "int": is_int,
    "seconds": lambda v: is_int(v, 1, SECONDS_LIMIT),
    "limit": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool) and 0 <= v <= MAX_CRAP_LIMIT,
    "suffix": lambda v: isinstance(v, str) and bool(SUFFIX_PATTERN.fullmatch(v)),
    "text": is_free_text,
}


def lookup(section, key, path):
    data = load(path).get(section, {})
    return data.get(key, MISSING) if isinstance(data, dict) else MISSING


def get(section, key, default, kind, path=None):
    """One value of KIND, the default when the setting is absent, a refusal when it is invalid."""
    value = lookup(section, key, path)
    if value is MISSING:
        return default
    if not CHECKS[kind](value):
        refuse(f"{section}.{key}")
    return value


def get_list(section, key, default, kind, path=None):
    """A non-empty list whose every item is of KIND, the default when absent, a refusal otherwise."""
    value = lookup(section, key, path)
    if value is MISSING:
        return default
    if not (isinstance(value, list) and value and all(CHECKS[kind](item) for item in value)):
        refuse(f"{section}.{key}")
    return value


def split_command(text, label):
    """Argument list for a command string; refused when it needs a shell to mean what it says."""
    if not isinstance(text, str) or not text.strip() or len(text) > COMMAND_LIMIT or SHELL_METACHARACTERS & set(text):
        refuse(label)
    try:
        return shlex.split(text)
    except ValueError:
        refuse(label)


def get_command(section, key, path=None):
    value = lookup(section, key, path)
    return None if value is MISSING else split_command(value, f"{section}.{key}")


def operand(path):
    """A path for a tool's command line: never starts with "-", so it cannot be read as an option."""
    return "./" + path if path.startswith("-") else path


def quote(text):
    """Source text for output: control characters removed, cut to QUOTE_LIMIT, shown as data."""
    cleaned = "".join(character if character.isprintable() else " " for character in text).strip()
    return cleaned[:QUOTE_LIMIT] + ("..." if len(cleaned) > QUOTE_LIMIT else "")


def show_path(text):
    return text if is_path(text) else "<unprintable path>"


def show_name(text):
    return text if is_name(text) else "<function>"


def main(argv):
    config = os.environ.get("QG_CONFIG")
    if len(argv) == 4 and argv[1] == "check":
        if not CHECKS[argv[2]](argv[3]):
            refuse(f"the {argv[2]} argument")
        return
    if len(argv) != 5:
        sys.exit("usage: qg_config.py SECTION KEY DEFAULT path|paths|token  |  qg_config.py check path|token VALUE")
    section, key, default, kind = argv[1:]
    if kind == "paths":
        print("\n".join(get_list(section, key, default.split(), "path", config)))
    else:
        print(get(section, key, default, kind, config))


if __name__ == "__main__":
    main(sys.argv)
