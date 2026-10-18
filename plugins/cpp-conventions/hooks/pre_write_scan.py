#!/usr/bin/env python3
"""PreToolUse hook: scan the C++ text about to be written for copy smells and bare numbers.

Advisory: the report goes to Claude as additionalContext and the hook exits 0. A project opts in to
blocking per scanner with .claude/cpp-conventions.json, e.g. {"copies": {"block": true}}; the report
then goes to stderr with exit 2. Any exception exits 0: a broken hook must never break an edit.
"""
import json
import os
import pathlib
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))

BLOCK_EXIT = 2
REPORT_LIMIT = 12
IGNORED_NOTE = "A value in .claude/cpp-conventions.json was ignored (invalid); defaults were used."


def new_texts(tool_input):
    if isinstance(tool_input.get("content"), str):
        yield tool_input["content"]
    if isinstance(tool_input.get("new_string"), str):
        yield tool_input["new_string"]
    for edit in tool_input.get("edits") or []:
        if isinstance(edit, dict) and isinstance(edit.get("new_string"), str):
            yield edit["new_string"]


def run_scanners(path, text, config):
    import copy_scan
    import number_scan
    from cpp_text import rule_config

    reports = []
    copies = rule_config(config, "copies")
    if not copies.get("disable"):
        reports.append(("copies", bool(copies.get("block")), copy_scan.scan(text, path)))
    numbers = rule_config(config, "numbers")
    if not numbers.get("disable"):
        allow = numbers.get("allow", [])
        reports.append(("numbers", bool(numbers.get("block")), number_scan.scan(text, path, allow)))
    return reports


def render(path, reports):
    from cpp_text import safe_path

    shown_name = safe_path(os.path.basename(path), "the file")
    lines = []
    for _, _, findings in reports:
        lines.extend(f.render(shown_name) for f in findings)
    shown = lines[:REPORT_LIMIT]
    if len(lines) > REPORT_LIMIT:
        shown.append(f"... and {len(lines) - REPORT_LIMIT} more")
    return "\n".join(shown)


def main():
    from cpp_text import env_off, find_config, is_cpp_path, validate_config

    if env_off():
        return 0
    payload = json.load(sys.stdin)
    tool_input = payload.get("tool_input") or {}
    path = tool_input.get("file_path") or ""
    if not path or not is_cpp_path(path):
        return 0
    config, ignored = validate_config(find_config([os.path.dirname(path), payload.get("cwd"), os.environ.get("CLAUDE_PROJECT_DIR")]))
    reports = []
    for text in new_texts(tool_input):
        reports.extend(run_scanners(path, text, config))
    reports = [r for r in reports if r[2]]
    if not reports:
        return 0
    body = render(path, reports)
    if ignored:
        body += "\n" + IGNORED_NOTE
    blocking = any(block for _, block, _ in reports)
    if blocking:
        print("cpp-conventions (blocking, per .claude/cpp-conventions.json):\n" + body, file=sys.stderr)
        return BLOCK_EXIT
    context = (
        "cpp-conventions scan of the text you are about to write (advisory; load the skills named in the plugin README for the rules):\n"
        + body
        + "\nSilence a deliberate case with `// copy-ok: <ownership boundary>` or `// magic-ok: <source of the number>`."
    )
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": context}}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a broken hook must never break an edit
        sys.exit(0)
