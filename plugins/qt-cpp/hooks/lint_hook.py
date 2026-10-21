#!/usr/bin/env python3
"""PostToolUse hook: run the Qt model lint on the C++ file Claude just wrote or edited.

The lint needs whole functions (a begin and its end can be far apart), so it reads the file as it is on disk after
the edit, not the fragment that was written. Advisory: the report goes to Claude as additionalContext and the hook
exits 0. A project opts in to blocking per rule with .claude/qt-cpp.json, e.g. {"row-as-key": {"block": true}};
the report then goes to stderr with exit 2. Any exception exits 0: a broken hook must never break an edit.

Everything read from the repository is untrusted: the config (only booleans, fixed key names), the source (comments
and strings are blanked, an excerpt is capped and labelled as data) and the file name (shown only if it is plain).
"""
import json
import os
import pathlib
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))

BLOCK_EXIT = 2
REPORT_LIMIT = 12
MAX_FILE_BYTES = 1_000_000
UNREADABLE_NOTE = "The project config .claude/qt-cpp.json could not be read; defaults are used."
WRONG_TYPE_NOTE = "Ignored wrong-typed keys in .claude/qt-cpp.json: "
ADVICE_TAIL = "Silence a deliberate case with `// qt-model-ok: <reason>`. The skills item-model-contract-testing and qt-build-traps carry the rules."


def edited_path(payload):
    tool_input = payload.get("tool_input") or {}
    path = tool_input.get("file_path")
    return path if isinstance(path, str) else ""


def read_source(path):
    file = pathlib.Path(path)
    if not file.is_file() or file.stat().st_size > MAX_FILE_BYTES:
        return None
    return file.read_text(encoding="utf-8", errors="replace")


def enabled_rules(config):
    from cpp_text import RULES

    return [rule for rule in RULES if not config.get(rule, {}).get("disable")]


def excerpt_of(text, line):
    from cpp_text import mask, quoted_code

    masked = mask(text, drop_preprocessor=True).split("\n")
    return quoted_code(masked[line - 1]) if 0 < line <= len(masked) else ""


def render(path, text, findings):
    from cpp_text import safe_path

    name = safe_path(os.path.basename(path), "the file")
    shown = [f"{name}:{f.line}: [{f.rule}] {f.message} ({excerpt_of(text, f.line)})" for f in findings[:REPORT_LIMIT]]
    if len(findings) > REPORT_LIMIT:
        shown.append(f"... and {len(findings) - REPORT_LIMIT} more")
    return "\n".join(shown)


def notes(readable, wrong_keys):
    out = [] if readable else [UNREADABLE_NOTE]
    if wrong_keys:
        out.append(WRONG_TYPE_NOTE + ", ".join(wrong_keys) + ".")
    return out


def main():
    import qt_model_lint
    from cpp_text import env_off, find_config, is_cpp_path, validate_config

    payload = json.load(sys.stdin)
    path = edited_path(payload)
    if env_off() or not path or not is_cpp_path(path):
        return 0
    text = read_source(path)
    if text is None:
        return 0
    raw, readable = find_config([os.path.dirname(path), payload.get("cwd"), os.environ.get("CLAUDE_PROJECT_DIR")])
    config, wrong_keys = validate_config(raw)
    findings = qt_model_lint.scan(text, set(enabled_rules(config)))
    if not findings:
        return 0
    body = "\n".join([render(path, text, findings)] + notes(readable, wrong_keys))
    if any(config[f.rule].get("block") for f in findings):
        print("qt-cpp (blocking, per .claude/qt-cpp.json):\n" + body, file=sys.stderr)
        return BLOCK_EXIT
    context = "qt-cpp lint of the file you just wrote (advisory):\n" + body + "\n" + ADVICE_TAIL
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": context}}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a broken hook must never break an edit
        sys.exit(0)
