#!/usr/bin/env python3
import sys

import hook_common


def new_texts(tool_input):
    for key in hook_common.CONTENT_KEYS:
        if isinstance(tool_input.get(key), str):
            yield tool_input[key]
    for edit in tool_input.get("edits") or []:
        if isinstance(edit, dict):
            yield from (edit[key] for key in hook_common.CONTENT_KEYS if isinstance(edit.get(key), str))


def handle(root, relative, tool_input, config, allowances):
    found = [f for text in new_texts(tool_input) for f in hook_common.findings_in(relative, text, config, allowances)]
    if found:
        headline = f"The new text for {relative} repeats a definition or misses a C++26 idiom (line numbers count inside the new text). Rewrite it before it lands."
        hook_common.emit("PreToolUse", hook_common.report(headline, found, config))


def main():
    return hook_common.run(handle)


if __name__ == "__main__":
    sys.exit(main())
