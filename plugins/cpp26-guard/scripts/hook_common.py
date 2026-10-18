import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import cpp26_lint
import lint_common
import reflection_lint

REFLECTION_SKILL = "reflect-dont-hand-write"
IDIOMS_SKILL = "cpp26-idioms"
SKILL_OF_RULE = {**dict.fromkeys(reflection_lint.OWN_RULES, REFLECTION_SKILL), **dict.fromkeys(cpp26_lint.OWN_RULES, IDIOMS_SKILL)}
CONTENT_KEYS = ("content", "new_string", "newString")


def project_root(payload):
    return pathlib.Path(os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or ".").resolve()


def relative_path(raw, root):
    path = pathlib.Path(raw)
    return (path.resolve().relative_to(root) if path.is_absolute() else path).as_posix()


def findings_in(relative, text, config, allowances):
    enums = reflection_lint.collect_enums([text])
    found = list(reflection_lint.scan_text(relative, text, config, enums)) + list(cpp26_lint.scan_text(relative, text, config))
    return [f for f in found if not lint_common.is_allowed(f, allowances)]


def report(headline, found, config):
    skills = sorted({SKILL_OF_RULE[f.rule] for f in found})
    lines = [f"{headline} Skills: {', '.join(skills)}."]
    lines.extend(f"[{SKILL_OF_RULE[f.rule]}] {f.render(config)}" for f in found)
    lines.append(f"A real exception gets a justified line in {config.allowance_file} (path|rule|text fragment|reason); a reason starting 'pending:' marks debt to remove.")
    if config.ignored:
        lines.append(lint_common.IGNORED_NOTICE)
    return "\n".join(lines)


def emit(event, context):
    if context:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": event, "additionalContext": context}}))


def run(handler):
    try:
        payload = json.load(sys.stdin)
        tool_input = payload.get("tool_input") or payload.get("toolInput") or {}
        raw = tool_input.get("file_path") or tool_input.get("path") or ""
        root = project_root(payload)
        config = lint_common.load_config(root)
        relative = relative_path(raw, root)
        if raw and config.covers(relative):
            allowances = lint_common.project_allowances(root, config)
            handler(root, relative, tool_input, config, allowances)
    except (Exception, SystemExit):
        return 0
    return 0
