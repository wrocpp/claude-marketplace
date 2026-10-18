#!/usr/bin/env python3
"""Advisory scanner for bare numbers in C++ text.

Exempt, exactly: the values 0 and 1 in any spelling (0u, 1.0f, 0x0, 1s); 100 on a line that says
percent, pct or has a %; any number in a comment, string, character literal or preprocessor line;
enumerators; the initializer of a constexpr, consteval, constinit or const definition (including
static, inline and template-prefixed ones); a template parameter default; static_assert; the index
of std::get / std::tuple_element / std::variant_alternative; numbers in the allow list of
.claude/cpp-conventions.json; arguments of assertion macros (EXPECT_*, ASSERT_*, CHECK*, REQUIRE*,
assert) in test files; a line carrying `magic-ok: <reason>` on it or the line before.

Everything else is reported, including array sizes, default member initializers, default
arguments and `case` labels: give the number a name once and use the name.
"""
import argparse
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from cpp_text import Finding, has_marker, is_cpp_path, line_of, mask, safe_number  # noqa: E402

RULE = "numbers"
MARKER = "magic-ok"
PERCENT_VALUE = 100
BARE_VALUES = (0, 1)
MAX_REPORTED = 20

TOKEN = re.compile(
    r"""(?P<num>(?<![\w.])(?:0[xX][0-9a-fA-F']+|0[bB][01']+|(?:\d[\d']*(?:\.[\d']*)?|\.\d[\d']*)(?:[eE][+-]?\d+)?)\w*)
       |(?P<open>\{)|(?P<close>\})|(?P<semi>;)|(?P<lparen>\()|(?P<rparen>\))""",
    re.VERBOSE,
)
NUMBER_BODY = re.compile(r"0[xX][0-9a-fA-F]+|0[bB][01]+|\d+\.?\d*(?:[eE][+-]?\d+)?|\.\d+(?:[eE][+-]?\d+)?")
DEFINITION = re.compile(
    r"\s*(?:template\s*<[^;{}]*>\s*)?(?:\[\[[^\]]*\]\]\s*)?(?:(?:static|inline|extern|thread_local)\s+)*(?:constexpr|constinit|consteval|const)\b"
)
TEMPLATE_DEFAULT = re.compile(r"\s*template\s*<[^>]*$")
INDEX_TEMPLATES = re.compile(r"\b(?:get|tuple_element|variant_alternative|in_place_index)\s*<\s*$")
STATIC_ASSERT = re.compile(r"\bstatic_assert\b")
TEST_MACRO = re.compile(r"\b(?:EXPECT_\w+|ASSERT_\w+|CHECK\w*|REQUIRE\w*|assert)\s*\(")
BLOCK_END = re.compile(r"(?:\)|\]|:|\b(?:else|do|try|noexcept|const|override|final|mutable|volatile))\s*$")
BLOCK_KEYWORD = re.compile(r"\b(?:struct|class|union|namespace|extern)\b")
ENUM = re.compile(r"\benum\b")
TRAILING_RETURN = re.compile(r"->[^=;]*$")
PERCENT_LINE = re.compile(r"%|percent|pct", re.IGNORECASE)
TEST_PATH = re.compile(r"(^|[/_.-])(tests?|spec)([/_.-]|$)", re.IGNORECASE)


def parse_value(token):
    body = NUMBER_BODY.match(token.replace("'", ""))
    if not body:
        return None
    text = body.group(0)
    try:
        if text[:2].lower() in ("0x", "0b"):
            return int(text, 0)
        if re.fullmatch(r"\d+", text):
            return int(text, 8) if len(text) > 1 and text[0] == "0" and set(text) <= set("01234567") else int(text)
        return float(text)
    except ValueError:
        return None


def classify_open(prefix):
    if ENUM.search(prefix):
        return "enum"
    stripped = prefix.rstrip()
    if not stripped or BLOCK_END.search(stripped) or TRAILING_RETURN.search(stripped):
        return "block"
    if BLOCK_KEYWORD.search(prefix) and "=" not in prefix:
        return "block"
    return "init"


class Frame:
    def __init__(self, kind, start):
        self.kind = kind
        self.start = start
        self.parens = 0


def is_test_path(path):
    return bool(path) and bool(TEST_PATH.search(str(path)))


def exempt(prefix, value, line_text, in_test, allow):
    if value in BARE_VALUES or value in allow:
        return True
    if value == PERCENT_VALUE and PERCENT_LINE.search(line_text):
        return True
    if DEFINITION.match(prefix) or TEMPLATE_DEFAULT.match(prefix):
        return True
    if STATIC_ASSERT.search(prefix) or INDEX_TEMPLATES.search(prefix):
        return True
    return in_test and bool(TEST_MACRO.search(prefix))


def scan(text, path="", allow=()):
    lines = text.splitlines()
    code = mask(text, drop_preprocessor=True)
    in_test = is_test_path(path)
    allowed = set(allow)
    stack = [Frame("block", 0)]
    findings = []
    for token in TOKEN.finditer(code):
        kind = token.lastgroup
        frame = stack[-1]
        if kind == "open":
            stack.append(Frame(classify_open(code[_block_frame(stack).start : token.start()]), token.end()))
        elif kind == "close":
            if len(stack) > 1:
                popped = stack.pop()
                if popped.kind != "init":
                    stack[-1].start = token.end()
        elif kind == "semi":
            if frame.parens == 0 and frame.kind != "init":
                frame.start = token.end()
        elif kind == "lparen":
            frame.parens += 1
        elif kind == "rparen":
            frame.parens = max(0, frame.parens - 1)
        else:
            owner = _block_frame(stack)
            if owner.kind == "enum":
                continue
            value = parse_value(token.group("num"))
            if value is None:
                continue
            number = line_of(code, token.start())
            line_text = lines[number - 1] if number <= len(lines) else ""
            prefix = code[owner.start : token.start()]
            if exempt(prefix, value, line_text, in_test, allowed) or has_marker(lines, number, MARKER):
                continue
            findings.append(
                Finding(number, RULE, f"bare number {safe_number(token.group('num'))}: name it once (constexpr, with its source) and use the name, or write `// {MARKER}: <reason>`")
            )
    return findings


def _block_frame(stack):
    for frame in reversed(stack):
        if frame.kind != "init":
            return frame
    return stack[0]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Report bare numbers in C++ files (advisory unless --check).")
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--allow", type=float, action="append", default=[], help="number to treat as named (repeatable)")
    parser.add_argument("--check", action="store_true", help="exit 1 when anything is reported (a guard test)")
    args = parser.parse_args(argv)
    total = 0
    for name in args.paths:
        path = pathlib.Path(name)
        files = sorted(p for p in path.rglob("*") if p.is_file() and is_cpp_path(p)) if path.is_dir() else [path]
        for file in files:
            for finding in scan(file.read_text(encoding="utf-8", errors="replace"), str(file), args.allow):
                print(finding.render(str(file)))
                total += 1
    print(f"{total} bare number(s)")
    return 1 if (args.check and total) else 0


if __name__ == "__main__":
    sys.exit(main())
