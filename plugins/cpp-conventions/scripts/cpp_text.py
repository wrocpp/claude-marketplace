"""Shared text helpers for the scanners: masking, path tests, project config.

The scanners read text, not compiler state. They never run a compiler and never import a project.
"""
import json
import os
import pathlib
import re

CPP_SUFFIXES = {".cpp", ".cc", ".cxx", ".c++", ".hpp", ".hh", ".hxx", ".h++", ".h", ".ipp", ".inl", ".tpp", ".cppm", ".ixx"}
CONFIG_RELATIVE = pathlib.Path(".claude") / "cpp-conventions.json"
MARKER_REASON = re.compile(r"[A-Za-z0-9_]")
RAW_STRING_OPEN = re.compile(r'R"([^()\\\s]{0,16})\(')


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


def _blank(chars):
    return "".join(c if c == "\n" else " " for c in chars)


def _consume_raw_string(text, i):
    opening = RAW_STRING_OPEN.match(text, i)
    if not opening:
        return None
    closing = ")" + opening.group(1) + '"'
    end = text.find(closing, opening.end())
    return len(text) if end < 0 else end + len(closing)


def _consume_quoted(text, i, quote):
    j = i + 1
    while j < len(text) and text[j] != "\n":
        if text[j] == "\\":
            j += 2
            continue
        if text[j] == quote:
            return j + 1
        j += 1
    return j


def _is_digit_separator(text, i):
    return i > 0 and (text[i - 1].isalnum()) and i + 1 < len(text) and text[i + 1].isalnum() and _in_number(text, i)


def _in_number(text, i):
    j = i - 1
    while j >= 0 and (text[j].isalnum() or text[j] in "'."):
        j -= 1
    return text[j + 1 : j + 2].isdigit() or (text[j + 1 : j + 2] == "." and text[j + 2 : j + 3].isdigit())


def mask(text, drop_preprocessor=False):
    """Blank comments, string and character literals (and, on request, preprocessor lines).

    Length and newlines are preserved, so offsets and line numbers still match the input.
    """
    out = []
    i = 0
    n = len(text)
    line_start = True
    while i < n:
        c = text[i]
        if c == "\n":
            out.append(c)
            i += 1
            line_start = True
            continue
        if line_start and c in " \t":
            out.append(c)
            i += 1
            continue
        if drop_preprocessor and line_start and c == "#":
            j = i
            while j < n:
                if text[j] == "\n" and text[j - 1] != "\\":
                    break
                j += 1
            out.append(_blank(text[i:j]))
            i = j
            continue
        line_start = False
        if text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j < 0 else j
            out.append(_blank(text[i:j]))
            i = j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            out.append(_blank(text[i:j]))
            i = j
        elif c == "R" and text.startswith('R"', i) and (i == 0 or not (text[i - 1].isalnum() or text[i - 1] == "_")):
            j = _consume_raw_string(text, i)
            if j is None:
                out.append(c)
                i += 1
            else:
                out.append(_blank(text[i:j]))
                i = j
        elif c == '"':
            j = _consume_quoted(text, i, '"')
            out.append(_blank(text[i:j]))
            i = j
        elif c == "'" and not _is_digit_separator(text, i):
            j = _consume_quoted(text, i, "'")
            out.append(_blank(text[i:j]))
            i = j
        else:
            out.append(c)
            i += 1
    return "".join(out)


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


def find_config(start_dirs):
    seen = set()
    for start in start_dirs:
        if not start:
            continue
        directory = pathlib.Path(start).resolve()
        for candidate in (directory, *directory.parents):
            if candidate in seen:
                break
            seen.add(candidate)
            config = candidate / CONFIG_RELATIVE
            if config.is_file():
                try:
                    loaded = json.loads(config.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    return {}
                return loaded if isinstance(loaded, dict) else {}
    return {}


def rule_config(config, rule):
    value = config.get(rule, {})
    return value if isinstance(value, dict) else {}


def env_off():
    return os.environ.get("CPP_CONVENTIONS_OFF") == "1"
