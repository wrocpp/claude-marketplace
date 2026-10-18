"""Reads .claude/cpp-quality-gates.json. The file belongs to the project, so it is untrusted.

Every value is validated by type before use and is never echoed: an invalid value is ignored,
the default applies, and stderr names only the setting (section.key), never its content.
"""
import json
import os
import pathlib
import re
import sys

CONFIG_PATH = pathlib.Path(".claude/cpp-quality-gates.json")
PATH_PATTERN = re.compile(r"^[A-Za-z0-9_./-]{1,128}$")
TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_.+-]{1,64}$")
SUFFIX_PATTERN = re.compile(r"^\.[A-Za-z0-9]{1,8}$")
NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_:<>]{0,63}$")
QUOTE_LIMIT = 120
NUMBER_LIMIT = 1_000_000
MISSING = object()
RETIRED_KEYS = (("mutation", "build"), ("mutation", "test"))


def load(path=None):
    path = pathlib.Path(path) if path else CONFIG_PATH
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        warn("config", "file")
        return {}
    return data if isinstance(data, dict) else {}


def warn(section, key):
    print(f"cpp-quality-gates: ignored an invalid config value ({section}.{key})", file=sys.stderr)


def is_path(value):
    return isinstance(value, str) and bool(PATH_PATTERN.match(value)) and ".." not in value.split("/") and not value.startswith("/")


def is_token(value):
    return isinstance(value, str) and bool(TOKEN_PATTERN.match(value))


def is_name(value):
    return isinstance(value, str) and bool(NAME_PATTERN.match(value))


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value <= NUMBER_LIMIT


def is_free_text(value):
    return isinstance(value, str) and 0 < len(value) <= QUOTE_LIMIT and value.isprintable()


CHECKS = {"path": is_path, "token": is_token, "number": is_number, "suffix": lambda v: isinstance(v, str) and bool(SUFFIX_PATTERN.match(v)), "text": is_free_text}


def lookup(section, key, path):
    data = load(path).get(section, {})
    return data.get(key, MISSING) if isinstance(data, dict) else MISSING


def get(section, key, default, kind, path=None):
    """One value of KIND (path, token, number, suffix, text) or the default."""
    value = lookup(section, key, path)
    if value is MISSING:
        return default
    if CHECKS[kind](value):
        return value
    warn(section, key)
    return default


def get_list(section, key, default, kind, path=None):
    """A non-empty list whose every item is of KIND, or the default."""
    value = lookup(section, key, path)
    if value is MISSING:
        return default
    if isinstance(value, list) and value and all(CHECKS[kind](item) for item in value):
        return value
    warn(section, key)
    return default


def report_retired(path=None):
    """Settings that used to carry shell commands are never run; say so by key name."""
    for section, key in RETIRED_KEYS:
        if lookup(section, key, path) is not MISSING:
            print(f"cpp-quality-gates: {section}.{key} in the config is not run; pass --{key} on the command line", file=sys.stderr)


def quote(text):
    """Source text for output: control characters removed, cut to QUOTE_LIMIT, shown as data."""
    cleaned = "".join(character if character.isprintable() else " " for character in text).strip()
    return cleaned[:QUOTE_LIMIT] + ("..." if len(cleaned) > QUOTE_LIMIT else "")


def show_path(text):
    return text if is_path(text) else "<unprintable path>"


def show_name(text):
    return text if is_name(text) else "<function>"


def main(argv):
    if len(argv) != 5:
        sys.exit("usage: qg_config.py SECTION KEY DEFAULT path|paths|token|number")
    section, key, default, kind = argv[1:]
    config = os.environ.get("QG_CONFIG")
    if kind == "paths":
        value = get_list(section, key, default.split(), "path", config)
        print(" ".join(value))
    else:
        print(get(section, key, default, kind, config))


if __name__ == "__main__":
    main(sys.argv)
