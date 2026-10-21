#!/usr/bin/env python3
"""Text lint for Qt item models written in C++.

Four rules, each a mistake that compiled and passed a check on the model's own data (see the skills):

  begin-end-pairing           a begin*Rows/Columns/ResetModel call with no matching end* in the same function
  dependent-base-connect      unqualified connect( in a class template whose base depends on a template parameter
  row-as-key                  data() answers a role named like a key with the row
  fromvalue-in-template-emit  QVariant::fromValue( at an emit site inside a template

The lint reads text with comments, strings and character literals blanked. It does not parse C++: a function is a
brace block at namespace or class scope, a lambda belongs to the function that contains it, and a class template
is found by its `template <...> class X : bases {` header. Out-of-class member definitions of a class template
are not recognised by the dependent-base rule. A finding is silenced with `// qt-model-ok: <reason>` on its line
or the line before.

    qt_model_lint.py [--rule NAME ...] path...     paths are files or directories; exit 1 when there is a finding
"""
import argparse
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from cpp_text import Finding, has_marker, is_cpp_path, line_of, mask  # noqa: E402

MARKER = "qt-model-ok"
MAX_FILE_BYTES = 1_000_000

BEGIN_END = {
    "beginInsertRows": "endInsertRows",
    "beginRemoveRows": "endRemoveRows",
    "beginMoveRows": "endMoveRows",
    "beginInsertColumns": "endInsertColumns",
    "beginRemoveColumns": "endRemoveColumns",
    "beginMoveColumns": "endMoveColumns",
    "beginResetModel": "endResetModel",
}
SCOPE_HEADER = re.compile(r"\s*(?:\w+\s+)*?(?:namespace|class|struct|union|enum|extern)\b")
TEMPLATE_HEAD = re.compile(r"\btemplate\s*<")
CLASS_TEMPLATE_HEADER = re.compile(r"\s*(?:class|struct)\s+\w+\s*(?:<[^{};]*?>)?\s*(?:final\s*)?:(?!:)\s*([^{};]+?)\{")
UNQUALIFIED_CONNECT = re.compile(r"(?<![\w:.>~])connect\s*\(")
DATA_FUNCTION = re.compile(
    r"\bdata\s*\(\s*(?:const\s+QModelIndex|QModelIndex\s+const)\s*&\s*(\w+)\s*,\s*int\s+(\w+)[^)]*\)\s*const\s*(?:override\s*|final\s*)?\{"
)
KEY_WORDS = {"key", "id", "uid", "identity", "ident"}
ROLE_COMPARISON = r"(?:\b{role}\s*==\s*([\w:]+)|([\w:]+)\s*==\s*\b{role}\b|\bcase\s+([\w:]+)\s*:)"
RETURN_STATEMENT = re.compile(r"\breturn\b([^;]*);")
ROW_ASSIGNMENT = re.compile(r"\b(\w+)\s*(?:=|\{)\s*([^;{}]*\.row\(\)[^;{}]*)")
EMIT_STATEMENT = re.compile(r"\b(?:emit|Q_EMIT)\b([^;]*);")
ROW_WRAPPERS = {"QVariant", "fromValue", "static_cast", "int", "qsizetype", "qint64", "quint64", "uint", "unsigned", "long", "size_t", "QString", "number", "const"}
NOT_A_CALL_BEFORE = {"return", "else", "do", "co_return", "case"}


# ---- text structure -------------------------------------------------------------------------------------------

def matching_close(text, open_at, opener="{", closer="}"):
    """The offset of the bracket that closes the one at open_at, or len(text) when it is never closed."""
    depth = 0
    for i in range(open_at, len(text)):
        depth += text[i] == opener
        depth -= text[i] == closer
        if depth == 0:
            return i
    return len(text)


def strip_template_heads(header):
    out = header
    for found in reversed(list(TEMPLATE_HEAD.finditer(header))):
        close = matching_close(header, found.end() - 1, "<", ">")
        out = out[: found.start()] + out[close + 1 :] if close < len(header) else out[: found.start()]
    return out


def is_scope_header(header):
    return "(" not in header and bool(SCOPE_HEADER.match(strip_template_heads(header)))


def function_blocks(masked):
    """(start, end) of every brace block at namespace or class scope that is not itself a scope.

    A lambda or a control block inside is part of the block that holds it, so a begin in one lambda and its end in
    the next lambda of the same function pair up.
    """
    blocks = []
    header_start = 0
    i = 0
    while i < len(masked):
        char = masked[i]
        if char in ";}":
            header_start = i + 1
        elif char == "{" and is_scope_header(masked[header_start:i]):
            header_start = i + 1
        elif char == "{":
            close = matching_close(masked, i)
            blocks.append((i, close))
            i = close
            header_start = close + 1
        i += 1
    return blocks


def template_spans(masked):
    """(start, end) of every template declaration that has a body: a class, a function or a member."""
    spans = []
    for found in TEMPLATE_HEAD.finditer(masked):
        after_params = matching_close(masked, found.end() - 1, "<", ">") + 1
        brace = first_outside_parens(masked, after_params, "{;")
        if brace < len(masked) and masked[brace] == "{":
            spans.append((found.start(), matching_close(masked, brace)))
    return spans


def first_outside_parens(text, start, wanted):
    depth = 0
    for i in range(start, len(text)):
        depth += text[i] == "("
        depth -= text[i] == ")"
        if depth <= 0 and text[i] in wanted:
            return i
    return len(text)


def template_parameter_names(header_params):
    names = set()
    for parameter in split_top_level(header_params):
        declared = parameter.split("=")[0]
        words = re.findall(r"[A-Za-z_]\w*", declared)
        if words:
            names.add(words[-1])
    return names


def split_top_level(text):
    parts, depth, current = [], 0, []
    for char in text:
        depth += char in "<(["
        depth -= char in ">)]"
        if char == "," and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(char)
    parts.append("".join(current))
    return parts


# ---- rule 1: begin without end ---------------------------------------------------------------------------------

def unpaired_begins(masked, block):
    body = masked[block[0] : block[1] + 1]
    for begin, end in BEGIN_END.items():
        calls = [m.start() for m in re.finditer(rf"\b{begin}\s*\(", body)]
        ends = len(re.findall(rf"\b{end}\s*\(", body))
        if len(calls) > ends:
            yield begin, end, block[0] + calls[ends]


def check_begin_end_pairing(masked, lines):
    for block in function_blocks(masked):
        for begin, end, offset in unpaired_begins(masked, block):
            message = (
                f"{begin} has no matching {end} in the same function. Every begin is followed by its end, once, "
                "or a view is left with a half-announced change. If the end is in the paired slot, say so with "
                f"`// {MARKER}: <where the end is>`."
            )
            yield Finding(line_of(masked, offset), "begin-end-pairing", message)


# ---- rule 2: unqualified connect in a class template with a dependent base -------------------------------------

def dependent_class_bodies(masked):
    """(body start, body end) of each class template whose base list names a template parameter."""
    for head in TEMPLATE_HEAD.finditer(masked):
        params_end = matching_close(masked, head.end() - 1, "<", ">")
        names = template_parameter_names(masked[head.end() : params_end])
        header = CLASS_TEMPLATE_HEADER.match(masked, params_end + 1)
        if header and any(re.search(rf"\b{re.escape(name)}\b", header.group(1)) for name in names):
            brace = header.end() - 1
            yield brace, matching_close(masked, brace)


def declares_connect(body):
    return bool(re.search(r"\b\w+[\w:<>*&\s]*\s[*&]*connect\s*\([^)]*\)\s*(?:const)?\s*[{;]", body))


def previous_word(text, offset):
    found = re.search(r"(\w+)\s*$", text[:offset])
    return found.group(1) if found else ""


def is_call_position(before):
    """True when `connect(` starts an expression; after a type name it is a declaration."""
    trimmed = before.rstrip()
    return not trimmed or trimmed[-1] in "=(,{};)!&|?:" or previous_word(trimmed, len(trimmed)) in NOT_A_CALL_BEFORE


def unqualified_connect_calls(masked, start, end):
    body = masked[start:end]
    if declares_connect(body):
        return
    for call in UNQUALIFIED_CONNECT.finditer(body):
        if is_call_position(body[: call.start()]):
            yield start + call.start()


def check_dependent_base_connect(masked, lines):
    message = (
        "unqualified connect() in a class template whose base depends on a template parameter: ordinary lookup does "
        "not enter a dependent base, so argument-dependent lookup picks whatever function called connect it finds, "
        "with no diagnostic. Write QObject::connect or this->connect."
    )
    for start, end in dependent_class_bodies(masked):
        for offset in unqualified_connect_calls(masked, start, end):
            yield Finding(line_of(masked, offset), "dependent-base-connect", message)


# ---- rule 3: a key role that answers with the row --------------------------------------------------------------

def is_key_role_name(name):
    words = re.findall(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+", name.split("::")[-1])
    lowered = {word.lower() for word in words}
    return "role" in lowered and bool(lowered & KEY_WORDS)


def row_derived(expression, row_names):
    """True when the expression is the row itself, however it is cast, boxed or scaled.

    A lookup keyed by the row (`m_entries.at(index.row()).id`) is an id that belongs to the entry, not the row.
    """
    rest = re.sub(r"\b\w+\s*(?:\.|->)\s*row\s*\(\s*\)", " ", expression)
    had_row = rest != expression
    for name in row_names:
        renamed = re.sub(rf"\b{re.escape(name)}\b", " ", rest)
        had_row, rest = had_row or renamed != rest, renamed
    return had_row and all(word in ROW_WRAPPERS for word in re.findall(r"[A-Za-z_]\w*", rest))


def key_role_segments(body, role_name):
    """(role constant, text that follows its comparison up to the next one) for each key-like role."""
    pattern = re.compile(ROLE_COMPARISON.format(role=re.escape(role_name)))
    matches = list(pattern.finditer(body))
    for position, match in enumerate(matches):
        constant = next(group for group in match.groups() if group)
        if is_key_role_name(constant):
            stop = matches[position + 1].start() if position + 1 < len(matches) else len(body)
            yield constant, match.end(), body[match.end() : stop]


def rows_returned_for_keys(body, role_name):
    row_names = {m.group(1) for m in ROW_ASSIGNMENT.finditer(body) if row_derived(m.group(2), ())}
    for constant, offset, segment in key_role_segments(body, role_name):
        for statement in RETURN_STATEMENT.finditer(segment):
            if row_derived(statement.group(1), row_names):
                yield constant, offset + statement.start()


def check_row_as_key(masked, lines):
    for function in DATA_FUNCTION.finditer(masked):
        body_start = function.end() - 1
        body = masked[body_start : matching_close(masked, body_start) + 1]
        for constant, offset in rows_returned_for_keys(body, function.group(2)):
            message = (
                "data() answers a key-named role with the row. A row shifts under every insert and remove "
                "with no signal, so a sorting proxy or a view that caches the value goes stale. Offer no key role "
                "for a list, or return an id that belongs to the entry."
            )
            yield Finding(line_of(masked, body_start + offset), "row-as-key", message)


# ---- rule 4: QVariant::fromValue at an emit inside a template --------------------------------------------------

def check_fromvalue_in_template_emit(masked, lines):
    spans = template_spans(masked)
    message = (
        "QVariant::fromValue at an emit inside a template: the signal boxes its argument, so the type must be a "
        "registered metatype, and a pointer to a class template specialization needs a normalized class name or Qt "
        "aborts when it registers it (skill qt-build-traps)."
    )
    for statement in EMIT_STATEMENT.finditer(masked):
        inside = any(start <= statement.start() <= end for start, end in spans)
        if inside and re.search(r"\bQVariant\s*::\s*fromValue\b", statement.group(1)):
            yield Finding(line_of(masked, statement.start()), "fromvalue-in-template-emit", message)


# ---- driver ----------------------------------------------------------------------------------------------------

CHECKS = {
    "begin-end-pairing": check_begin_end_pairing,
    "dependent-base-connect": check_dependent_base_connect,
    "row-as-key": check_row_as_key,
    "fromvalue-in-template-emit": check_fromvalue_in_template_emit,
}


def scan(text, rules=None):
    """Findings for one file's text, ordered by line, minus those silenced with a marker."""
    masked = mask(text, drop_preprocessor=True)
    lines = text.split("\n")
    found = []
    for rule, check in CHECKS.items():
        if rules is None or rule in rules:
            found.extend(check(masked, lines))
    quiet = [f for f in found if not has_marker(lines, f.line, MARKER)]
    return sorted(quiet, key=lambda f: (f.line, f.rule))


def cpp_files(paths):
    for path in paths:
        if path.is_dir():
            yield from sorted(p for p in path.rglob("*") if p.is_file() and is_cpp_path(str(p)))
        elif path.is_file():
            yield path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--rule", action="append", choices=sorted(CHECKS), help="only this rule (repeatable)")
    parser.add_argument("paths", nargs="+", type=pathlib.Path)
    args = parser.parse_args(argv)
    total = 0
    for path in cpp_files(args.paths):
        if path.stat().st_size > MAX_FILE_BYTES:
            continue
        for finding in scan(path.read_text(encoding="utf-8", errors="replace"), args.rule):
            print(finding.render(str(path)))
            total += 1
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
