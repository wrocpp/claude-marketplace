#!/usr/bin/env python3
"""Build every target that must not build and check that it fails the way its first line says.

Usage: check_reject.py <cmake build dir> <tests dir>
A reject fixture starts with `// expect-error: <regex>`; the build must fail and its output must match.
The accept side of each pair is built by the normal build, so a fixture that fails for another reason (a typo,
a missing include) is caught by its control compiling.
"""
import pathlib
import re
import subprocess
import sys

EXPECT = re.compile(r"^// expect-error: (.+)$", re.MULTILINE)
BUILD_SECONDS = 300


def fixtures(tests):
    reject = tests / "cpp" / "reject"
    for source in sorted(reject.glob("*.cpp")):
        yield source.stem, source
    for source in sorted(reject.glob("*/a.cpp")):
        yield source.parent.name, source


def check(build, name, source):
    found = EXPECT.search(source.read_text(encoding="utf-8"))
    if not found:
        return f"{source.name}: no `// expect-error:` line"
    result = subprocess.run(["cmake", "--build", str(build), "--target", f"reject_{name}"], capture_output=True, text=True, timeout=BUILD_SECONDS)
    output = result.stdout + result.stderr
    if result.returncode == 0:
        return f"{name}: built, but it must not"
    if not re.search(found.group(1), output):
        return f"{name}: failed, but not with /{found.group(1)}/:\n{output[-1500:]}"
    print(f"ok   rejected {name} (/{found.group(1)}/)")
    return None


def main():
    build, tests = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    problems = [p for p in (check(build, n, s) for n, s in fixtures(tests)) if p]
    for problem in problems:
        print("FAIL " + problem)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
