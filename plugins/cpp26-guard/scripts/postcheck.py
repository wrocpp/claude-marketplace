#!/usr/bin/env python3
import sys

import hook_common
import lint_common


def handle(root, relative, tool_input, config, allowances):
    path = root / relative
    if not path.is_file():
        return
    found = hook_common.findings_in(relative, path.read_text(encoding="utf-8", errors="replace"), config, allowances)
    if found:
        hook_common.emit("PostToolUse", hook_common.report(f"{lint_common.display_path(relative)} now repeats a definition or misses a C++26 idiom.", found, config))


def main():
    return hook_common.run(handle)


if __name__ == "__main__":
    sys.exit(main())
