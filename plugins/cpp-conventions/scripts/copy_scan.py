#!/usr/bin/env python3
"""Advisory scanner for common copy smells in C++ text.

Rules (each line of output names its rule id):
  param-const-ref   a const std::string& / const std::vector<T>& parameter: borrow with
                    std::string_view / std::span<const T> unless the function stores the value
  sink-copy         such a parameter is stored in a member (`member_(p)`, `member_ = p`): take it
                    by value and std::move it
  range-for-copy    `for (std::string s : xs)`: an explicit standard-container loop variable
                    without a reference copies every element
  substr-copy       `.substr(`: on std::string it allocates, on std::string_view it does not
  return-move       `return std::move(local);` of a local declared in the same text: it blocks
                    copy elision
  view-of-temporary a std::string_view / std::span initialised from a temporary
  view-return-temp  a function returning std::string_view that returns a std::string it just built
  copy-from-name    `std::string s = other;` copy-initialisation from a plain name
  cstr-roundtrip    std::string(x.c_str())
  ref-capture-escape  a [&] lambda handed to std::thread / std::jthread / std::async, or .detach()

Silence a line with `copy-ok: <the ownership boundary>` on it or the line before. The reason is
required: a copy that names no boundary is the smell.

Not caught: anything that needs types (auto, aliases, templates, overload resolution), a by-value
parameter that is never moved, a copy hidden behind a function return, shared_ptr that could be
shared_ptr<const T>. clang-tidy (performance-*) sees types; this scanner only sees text.
"""
import argparse
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from cpp_text import Finding, has_marker, is_cpp_path, line_of, mask  # noqa: E402

RULE = "copies"
MARKER = "copy-ok"

HEAVY = r"std::(?:string|wstring|vector\s*<[^;(){}]*>|map\s*<[^;(){}]*>|unordered_map\s*<[^;(){}]*>|set\s*<[^;(){}]*>|unordered_set\s*<[^;(){}]*>|deque\s*<[^;(){}]*>|list\s*<[^;(){}]*>)"
PARAM = re.compile(r"[(,]\s*const\s+(?P<type>" + HEAVY + r")\s*&\s*(?P<name>\w+)\s*(?=[,)=])")
RANGE_FOR = re.compile(r"\bfor\s*\(\s*(?:const\s+)?(?P<type>" + HEAVY + r")\s+(?P<name>\w+)\s*:")
SUBSTR = re.compile(r"\.\s*substr\s*\(")
RETURN_MOVE = re.compile(r"\breturn\s+std::move\s*\(\s*(?P<name>[A-Za-z_]\w*)\s*\)\s*;")
VIEW_TEMP = re.compile(
    r"\bstd::(?:string_view|span\s*<[^;(){}]*>)\s+\w+\s*(?:=|\{|\()\s*"
    r"(?:std::string\s*[({]|std::to_string\s*\(|std::format\s*\(|std::vformat\s*\(|std::vector\s*<[^;(){}]*>\s*[({]|std::ostringstream\b|[\w.>-]+\.str\s*\(\s*\)\s*[;)}])"
)
VIEW_RETURN = re.compile(r"\bstd::string_view\s+\w+\s*\([^;{}]*\)[^;{}]*\{[^{}]*?\breturn\s+std::(?:string|to_string|format)\b")
COPY_FROM_NAME = re.compile(r"(?:^|[;{}])\s*(?:const\s+)?(?P<type>" + HEAVY + r")\s+\w+\s*=\s*(?P<src>[A-Za-z_]\w*)\s*;", re.MULTILINE)
CSTR_ROUNDTRIP = re.compile(r"\bstd::string\s*[({]\s*[\w.>()-]*\.c_str\s*\(\s*\)\s*[)}]")
REF_CAPTURE = re.compile(r"\bstd::(?:(?:thread|jthread)(?:\s+\w+)?|async)\s*[({][^;]*?\[\s*&")
DETACH = re.compile(r"\.\s*detach\s*\(\s*\)")


def local_declaration(code, name):
    return re.search(r"\b(?:std::[\w:]+(?:\s*<[^;(){}]*>)?|auto)\s+" + re.escape(name) + r"\s*(?:[=;({])", code)


def stores_param(code, name, after):
    member_init = re.compile(r"\b\w+\s*[({]\s*" + re.escape(name) + r"\s*[)}]")
    member_assign = re.compile(r"(?:\bthis\s*->\s*\w+|\b\w+_)\s*=\s*" + re.escape(name) + r"\s*;")
    tail = code[after:]
    return bool(member_init.search(tail[: _body_window(tail)]) or member_assign.search(tail[: _body_window(tail)]))


def _body_window(tail):
    depth = 0
    for i, c in enumerate(tail):
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth <= 0:
                return i + 1
        elif c == ";" and depth == 0:
            return i + 1
    return len(tail)


def scan(text, path=""):
    code = mask(text)
    lines = text.splitlines()
    raw = []

    def add(offset, rule, message):
        raw.append(Finding(line_of(code, offset), rule, message))

    for hit in PARAM.finditer(code):
        name = hit.group("name")
        borrow = "std::string_view" if "string" in hit.group("type") else "std::span<const T>"
        if stores_param(code, name, hit.end()):
            add(hit.start(), "sink-copy", f"`{name}` is stored by copy: take it by value and std::move it into the member (sink parameter)")
        else:
            add(hit.start(), "param-const-ref", f"`const {hit.group('type')}& {name}` only borrows: prefer {borrow} unless it is stored or needs a terminator")
    for hit in RANGE_FOR.finditer(code):
        add(hit.start(), "range-for-copy", f"loop variable `{hit.group('name')}` copies every element: write `const {hit.group('type')}&`")
    for hit in SUBSTR.finditer(code):
        add(hit.start(), "substr-copy", "substr on std::string allocates: take a std::string_view first when you only look at the piece")
    for hit in RETURN_MOVE.finditer(code):
        name = hit.group("name")
        if local_declaration(code[: hit.start()], name) and not re.search(r"&&\s*" + re.escape(name) + r"\b", code):
            add(hit.start(), "return-move", f"`return std::move({name});` blocks copy elision of a local: return `{name}`")
    for hit in VIEW_TEMP.finditer(code):
        add(hit.start(), "view-of-temporary", "a view of a temporary dangles at the end of the statement: keep the owner in a named variable")
    for hit in VIEW_RETURN.finditer(code):
        add(hit.end(), "view-return-temp", "returning a view of a std::string built here dangles: return std::string")
    for hit in COPY_FROM_NAME.finditer(code):
        add(hit.start("type"), "copy-from-name", f"copy of `{hit.group('src')}`: bind a reference or view unless this is an ownership boundary you can name")
    for hit in CSTR_ROUNDTRIP.finditer(code):
        add(hit.start(), "cstr-roundtrip", "std::string(x.c_str()) copies bytes you already hold in a std::string")
    for hit in REF_CAPTURE.finditer(code):
        add(hit.start(), "ref-capture-escape", "a [&] lambda given to a thread/async outlives its captures: capture by value or move")
    for hit in DETACH.finditer(code):
        add(hit.start(), "ref-capture-escape", "a detached thread outlives the scope: hand it owned data, not references")

    unique = {}
    for finding in sorted(raw, key=lambda f: (f.line, f.rule)):
        if not has_marker(lines, finding.line, MARKER):
            unique.setdefault((finding.line, finding.rule), finding)
    return list(unique.values())


def main(argv=None):
    parser = argparse.ArgumentParser(description="Report copy smells in C++ files (advisory unless --check).")
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--check", action="store_true", help="exit 1 when anything is reported")
    args = parser.parse_args(argv)
    total = 0
    for name in args.paths:
        path = pathlib.Path(name)
        files = sorted(p for p in path.rglob("*") if p.is_file() and is_cpp_path(p)) if path.is_dir() else [path]
        for file in files:
            for finding in scan(file.read_text(encoding="utf-8", errors="replace"), str(file)):
                print(finding.render(str(file)))
                total += 1
    print(f"{total} copy smell(s)")
    return 1 if (args.check and total) else 0


if __name__ == "__main__":
    sys.exit(main())
