#!/usr/bin/env python3
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import cpp_source
import lint_common
from lint_common import Config, Finding, expect, is_allowed

MIN_RUN = 3
MIN_CHAIN = 4
MIN_JSON_KEYS = 3
MIN_WORDS = 3
MIN_STRING_ARMS = 2
CHAIN_WINDOW = 12
RUN_GAP_CHARS = " \t\r\n,"
COUNT_SPELLINGS = ("enum_count", "enumerators_of", "count_of")

STRING = r'"(?:[^"\\\n]|\\.)*"'
QUALIFIED = r"[\w:]+::\w+"
STRING_VALUE = rf"(?:{STRING}|std::string(?:_view)?\{{[^}}]*\}})"
ENUM_STRING_CASE = re.compile(rf"\bcase\s+{QUALIFIED}\s*:\s*(?:return\s+{STRING_VALUE}\s*;|break\s*;)")
ENUM_STRING_TERNARY = re.compile(rf'\w+\s*==\s*{QUALIFIED}\s*\?\s*{STRING}\s*:')
NAME_ENUM_PAIR = re.compile(rf"\{{\s*{STRING}\s*,\s*{QUALIFIED}\s*\}}")
HANDLER_PAIR = re.compile(rf"\{{\s*{QUALIFIED}\s*,\s*&[\w:]+\s*\}}")
ROUTE_ROW = re.compile(rf'\{{\s*"[A-Z]+"\s*,\s*{STRING}\s*,\s*{QUALIFIED}\s*\}}')
WORD_COMPARISON = re.compile(rf"\bif\s*\(\s*(?:[\w.\[\]]+)\s*==\s*{STRING}")
KEY_FROM_MEMBER = re.compile(r'\{\s*"(\w+)"\s*,.*\.\1\b.*')
JSON_PLACEHOLDER = re.compile(r'"\w+"\s*:\s*(?:\{\{)*"?\{\}"?')
ENUM_CAST_MODULO = re.compile(r"static_cast<\s*([\w:]+)\s*>\s*\(((?:[^;()]|\((?:[^;()]|\([^;()]*\))*\))*)%\s*([\w:]+)")
STRING_LIST = re.compile(r"std::to_array<\s*std::string_view\s*>\s*\(\s*\{(.*?)\}\s*\)", re.DOTALL)
ENUM_DEFINITION = re.compile(r"\benum\s+(?:class|struct)\s+(\w+)\s*(?::\s*[\w:\s]+?)?\s*\{([^}]*)\}")
ATTRIBUTE = re.compile(r"\[\[.*?\]\]", re.DOTALL)
ARITHMETIC_TYPE = re.compile(r"^(?:u?int(?:8|16|32|64|max|ptr)?_t|size_t|ptrdiff_t|ssize_t|int|unsigned|long|short|char|bool|double|float|time_t|off_t)$")

RULES = {
    lint_common.STALE: "remove the line from @allowance_file@, the code it excused is gone",
    "enum-name-switch": "an enum-to-string switch or ternary chain repeats the enumerator names; derive the name with @enum_name@",
    "name-enum-table": "a table of {\"word\", Type::member} pairs repeats the enumerator names; derive the lookup with @enum_from_name@",
    "word-chain": "a chain of if (word == \"...\") comparisons repeats member or flag names; annotate the members and walk them: @member_walk@",
    "key-member-block": "a block of {\"key\", x.key} pairs repeats member names; derive the object from the aggregate: @member_walk@",
    "json-format-template": "a std::format template spells out the keys of a JSON object; build the object from an aggregate and walk its members: @member_walk@",
    "enum-handler-table": "a table of {Enum::x, &fn} pairs must stay in step with the enum by hand; annotate the handlers with the enumerator and static_assert the dispatch is exhaustive",
    "route-table": "a table of {\"METHOD\", \"/path\", route::x} rows repeats the route enum; annotate the enumerators with the method and path",
    "enum-modulo": "static_cast<Enum>(n % N) hard-codes the enumerator count; use @enum_count@",
    "enum-word-list": "a std::to_array<std::string_view> word list repeats the enumerator names of an enum; use @enum_values@ with @enum_name@",
}
lint_common.ADVICE.update(RULES)
OWN_RULES = frozenset(RULES) - {lint_common.STALE}


def adjacent_runs(code, pattern, accept=lambda group: True):
    group = []
    for match in pattern.finditer(code):
        if group and code[group[-1].end() : match.start()].strip(RUN_GAP_CHARS):
            if len(group) >= MIN_RUN and accept(group):
                yield group[0]
            group = []
        group.append(match)
    if len(group) >= MIN_RUN and accept(group):
        yield group[0]


def has_string_arms(group):
    return sum("return" in m.group() for m in group) >= MIN_STRING_ARMS


def chains(lines):
    hits = [index for index, line in enumerate(lines) if WORD_COMPARISON.search(line)]
    group = []
    for index in hits:
        if group and index - group[-1] > CHAIN_WINDOW:
            if len(group) >= MIN_CHAIN:
                yield group[0]
            group = []
        group.append(index)
    if len(group) >= MIN_CHAIN:
        yield group[0]


def unquote(literal):
    return literal[1:-1].replace('\\"', '"')


def enumerators(body):
    names = []
    for part in ATTRIBUTE.sub("", body).split(","):
        found = re.match(r"\s*(\w+)", part)
        if found:
            names.append(found.group(1))
    return names


def collect_enums(texts):
    enums = {}
    for text in texts:
        for match in ENUM_DEFINITION.finditer(cpp_source.scan(text).code):
            enums[match.group(1)] = frozenset(enumerators(match.group(2)))
    return enums


def counted_by_reflection(modulus, config):
    spellings = COUNT_SPELLINGS + tuple(spelling for name, spelling in config.helpers if name == "enum_count")
    return any(spelling in modulus for spelling in spellings)


def raw_findings(path, text, config, enums):
    source = cpp_source.scan(text)
    code = source.code

    def found(rule, match):
        return Finding(path, source.line(match.start()), rule, source.text_at(match.start()))

    runs = (
        (ENUM_STRING_CASE, "enum-name-switch", has_string_arms),
        (NAME_ENUM_PAIR, "name-enum-table", lambda group: True),
        (HANDLER_PAIR, "enum-handler-table", lambda group: True),
        (ROUTE_ROW, "route-table", lambda group: True),
        (KEY_FROM_MEMBER, "key-member-block", lambda group: True),
    )
    for pattern, rule, accept in runs:
        for match in adjacent_runs(code, pattern, accept):
            yield found(rule, match)
    for match in ENUM_STRING_TERNARY.finditer(code):
        if source.text_at(match.start()).count("?") >= 2:
            yield found("enum-name-switch", match)
    for start in chains(code.splitlines()):
        yield Finding(path, start + 1, "word-chain", source.line_text(start + 1).strip())
    for literal in source.literals:
        if len(JSON_PLACEHOLDER.findall(literal.body.replace('\\"', '"'))) >= MIN_JSON_KEYS:
            yield Finding(path, literal.line, "json-format-template", source.line_text(literal.line).strip())
    for match in ENUM_CAST_MODULO.finditer(source.skeleton):
        if not ARITHMETIC_TYPE.match(match.group(1).split("::")[-1]) and not counted_by_reflection(match.group(3), config):
            yield Finding(path, source.line(match.start()), "enum-modulo", source.text_at(match.start()))
    for match in STRING_LIST.finditer(code):
        words = {unquote(word) for word in re.findall(STRING, match.group(1))}
        if len(words) >= MIN_WORDS and any(words <= names for names in (enums or {}).values()):
            yield found("enum-word-list", match)


def scan_text(path, text, config=Config(), enums=None):
    return list(dict.fromkeys(f for f in raw_findings(path, text, config, enums) if config.enabled(f.rule)))


def scan_paths(root, paths, config=Config()):
    allowances = lint_common.project_allowances(root, config)
    files = list(lint_common.source_files(root, paths, config))
    texts = {relative: file.read_text(encoding="utf-8", errors="replace") for relative, file in files}
    enums = collect_enums(texts.values())
    raw = [f for relative, text in texts.items() for f in scan_text(relative, text, config, enums)]
    kept = [f for f in raw if not is_allowed(f, allowances)]
    enabled = {rule for rule in OWN_RULES if config.enabled(rule)}
    return kept + lint_common.stale_allowances(allowances, raw, enabled, set(texts), root)


FIXTURES = {
    "enum-name-switch": 'constexpr auto f(E e) {\n  switch (e) {\n    case E::a: return "a";\n    case E::b: return "b";\n    case E::c: return "c";\n  }\n}\n',
    "name-enum-table": 'constexpr auto t = {\n  {"a", E::a},\n  {"b", E::b},\n  {"c", E::c},\n};\n',
    "word-chain": 'void p(std::string_view w) {\n if (w == "--a") {}\n else if (w == "--b") {}\n else if (w == "--c") {}\n else if (w == "--d") {}\n}\n',
    "key-member-block": 'auto j = make({\n {"input", n(s.input)},\n {"output", n(s.output)},\n {"cache", n(s.cache)},\n});\n',
    "json-format-template": 'auto j = std::format(R"({{"a":{},"b":{},"c":{{{}}}}})", x, y, z);\n',
    "enum-handler-table": 'constexpr auto h = std::to_array<H>({\n  {E::a, &f},\n  {E::b, &g},\n  {E::c, &x::h},\n});\n',
    "route-table": 'constexpr auto r = std::to_array<R>({\n  {"GET", "/a", route::a},\n  {"POST", "/b", route::b},\n  {"GET", "/c", route::c},\n});\n',
    "enum-modulo": "auto s = static_cast<doctor::state>(bits(c, 0, 3) % 5);\n",
}
CLEAN = (
    "void ok(E e) {\n  switch (e) {\n    case E::a: return 1;\n    case E::b: return 2;\n    case E::c: return 3;\n  }\n"
    '  if (w == "x") {}\n  if (w == "y") {}\n}\n{"a", 1},\n{"b", 2},\n'
    '// case E::a: return "a"; case E::b: return "b"; case E::c: return "c";\n'
    'auto raw = R"(case E::a: return "a"; case E::b: return "b"; case E::c: return "c";)";\n'
    'auto j = std::format(R"({{"a":{},"b":{}}})", x, y);\n'
    "auto n = static_cast<int>(x % 5);\nauto m = static_cast<std::uint8_t>(x % 5);\nauto u = static_cast<doctor::state>(x);\n"
    "auto k = static_cast<doctor::state>(x % enum_count<doctor::state>);\n"
    "auto q = static_cast<doctor::state>(x % std::meta::enumerators_of(^^doctor::state).size());\n"
)
TWO_LINE_SWITCH = 'switch (s) {\n  case status::pass:\n    return "PASS";\n  case status::warn:\n    return "WARN";\n  case status::fail:\n    return "FAIL";\n}\n'
ESCAPED_QUOTES = 'switch (s) {\n  case k::a: return "say \\"a\\"";\n  case k::b: return "say \\"b\\"";\n  case k::c: return "say \\"c\\"";\n}\n'
WORD_LIST = 'constexpr auto roles = std::to_array<std::string_view>({"opus", "sonnet", "haiku"});\n'
ESCAPED_JSON = 'auto j = std::format("{{\\"a\\":{},\\"b\\":{},\\"c\\":{}}}", x, y, z);\n'
ENUM_SOURCE = "enum class role { opus, sonnet, haiku, other };\n"
TERNARY = 'return s == level::a ? "a" : s == level::b ? "b" : "c";\n'
CUSTOM_COUNT = "auto k = static_cast<doctor::state>(x % mylib::size_of_enum<doctor::state>);\n"


def self_test():
    failures = 0
    for rule, text in FIXTURES.items():
        failures += expect(rule, scan_text("fixture.cppm", text), {rule})
    failures += expect("clean", scan_text("clean.cppm", CLEAN), set())
    failures += expect("ternary chain", scan_text("t.cppm", TERNARY), {"enum-name-switch"})
    failures += expect("two-line switch", scan_text("t.cppm", TWO_LINE_SWITCH), {"enum-name-switch"})
    failures += expect("escaped quotes", scan_text("t.cppm", ESCAPED_QUOTES), {"enum-name-switch"})
    failures += expect("escaped json template", scan_text("t.cppm", ESCAPED_JSON), {"json-format-template"})
    enums = collect_enums([ENUM_SOURCE])
    failures += expect("enum word list", scan_text("t.cppm", WORD_LIST, enums=enums), {"enum-word-list"})
    failures += expect("enum word list without the enum", scan_text("t.cppm", WORD_LIST), set())
    failures += expect("unrelated word list", scan_text("t.cppm", 'auto w = std::to_array<std::string_view>({"x", "y", "z"});\n', enums=enums), set())
    failures += expect("custom count helper", scan_text("t.cppm", CUSTOM_COUNT, Config(helpers=(("enum_count", "size_of_enum"),))), set())
    failures += expect("rule disabled", scan_text("t.cppm", FIXTURES["enum-name-switch"], Config(rules=(("enum-name-switch", False),))), set())
    return failures


def main(argv=None):
    return lint_common.run_cli("reflection_lint", "hand-written mirrors of a definition to review", scan_paths, self_test, argv)


if __name__ == "__main__":
    sys.exit(main())
