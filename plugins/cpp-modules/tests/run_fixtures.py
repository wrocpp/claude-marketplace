#!/usr/bin/env python3
"""Build every fixture under fixtures/ and compare the result with fixtures/expectations.json.

Usage: run_fixtures.py --cmake CMAKE --cxx COMPILER [--only NAME ...] [--observe]

A fixture is a tiny CMake project. Its expectation says how it ends: `builds` (configure, build and,
when it makes an executable named `app`, run), `fails` (a fragment of the output must appear) or
`crash` (the compiler reports an internal compiler error). `status` says what the entry documents:
`reproduced` (a trap), `fixed` (the workaround of a trap), `not-reproduced` (reported once, not
seen on the recorded compiler) or `works` (looks like a trap and is not) or `behaviour` (a documented
observable result that the fixture asserts itself). With --observe the
observed outcome is printed instead of compared, for writing a new expectation.
"""
import argparse
import concurrent.futures
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"
NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
ARGUMENT = re.compile(r"^(-G|Ninja|Unix Makefiles|-D[A-Z_]+=[A-Za-z0-9_./+ -]*)$")
OUTCOMES = ("builds", "fails", "crash")
STATUSES = ("reproduced", "fixed", "not-reproduced", "works", "behaviour")
STEP_TIMEOUT_SECONDS = 600
PARALLEL_FIXTURES = 3
CRASH_MARKER = "internal compiler error"
EVIDENCE_LINES = 3


def run(arguments, cwd=None):
    plain_messages = {**os.environ, "LC_ALL": "C", "LANGUAGE": ""}
    try:
        result = subprocess.run(arguments, cwd=cwd, env=plain_messages, capture_output=True, text=True, timeout=STEP_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        return 124, "timed out"
    return result.returncode, result.stdout + result.stderr


def compiler_version(cxx):
    code, output = run([cxx, "-dumpfullversion"])
    return output.strip() if code == 0 else "unknown"


def observe(cmake, cxx, source, extra):
    """Configure, build and run one fixture; return (outcome, output)."""
    build = pathlib.Path(tempfile.mkdtemp(prefix="wrocpp-fixture-"))
    try:
        generator = [] if "-G" in extra else ["-G", "Ninja"]
        code, output = run([cmake, "-S", str(source), "-B", str(build), *generator, f"-DCMAKE_CXX_COMPILER={cxx}", *extra])
        if code != 0:
            return "fails", output
        code, output = run([cmake, "--build", str(build)])
        if code != 0:
            return ("crash" if CRASH_MARKER in output else "fails"), output
        program = build / "app"
        if program.exists():
            code, output = run([str(program)])
            if code != 0:
                return "fails", f"run exited {code}: {output}"
        return "builds", output
    finally:
        shutil.rmtree(build, ignore_errors=True)


def evidence(output, fragment):
    lines = [line for line in output.splitlines() if fragment and fragment in line]
    interesting = lines or [line for line in output.splitlines() if re.search(r"error|undefined|Undefined|Error", line)]
    return [line.strip()[:200] for line in interesting[:EVIDENCE_LINES]]


def check(cmake, cxx, name, entry, version):
    source = FIXTURES / entry.get("fixture", name)
    if not NAME.match(name) or not source.joinpath("CMakeLists.txt").is_file():
        return name, False, "no such fixture directory"
    extra = entry.get("cmake_args", [])
    if not all(ARGUMENT.match(argument) for argument in extra):
        return name, False, f"cmake_args not allowed: {extra}"
    outcome, output = observe(cmake, cxx, source, extra)
    expected = entry["outcome"]
    fragment = entry.get("contains", "")
    if outcome != expected:
        note = f"expected {expected}, got {outcome}"
        if version not in entry.get("gcc", []):
            note += f" (recorded with GCC {', '.join(entry.get('gcc', []))}, compiler is {version})"
        return name, False, note + "".join(f"\n      {line}" for line in evidence(output, fragment))
    if outcome != "builds" and fragment not in output:
        return name, False, f"outcome {outcome} as expected but {fragment!r} is not in the output"
    return name, True, f"{entry['status']}: {outcome}"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cmake", required=True)
    parser.add_argument("--cxx", required=True)
    parser.add_argument("--only", nargs="*", default=[])
    parser.add_argument("--observe", action="store_true")
    arguments = parser.parse_args()
    expectations = json.loads((FIXTURES / "expectations.json").read_text(encoding="utf-8"))
    entries = {name: entry for name, entry in expectations["fixtures"].items() if not arguments.only or name in arguments.only}
    for name, entry in entries.items():
        if entry.get("outcome") not in OUTCOMES or entry.get("status") not in STATUSES:
            print(f"FAIL {name}: outcome or status is not one of {OUTCOMES} / {STATUSES}")
            return 1
    version = compiler_version(arguments.cxx)
    print(f"compiler {arguments.cxx} {version}, {len(entries)} fixtures")
    if arguments.observe:
        for name, entry in entries.items():
            outcome, output = observe(arguments.cmake, arguments.cxx, FIXTURES / entry.get("fixture", name), entry.get("cmake_args", []))
            print(f"{name}: {outcome} {evidence(output, entry.get('contains', ''))}")
        return 0
    failures = 0
    environment_workers = int(os.environ.get("WROCPP_FIXTURE_JOBS", PARALLEL_FIXTURES))
    with concurrent.futures.ThreadPoolExecutor(max_workers=environment_workers) as pool:
        futures = [pool.submit(check, arguments.cmake, arguments.cxx, name, entry, version) for name, entry in entries.items()]
        for future in futures:
            name, passed, note = future.result()
            print(f"{'PASS' if passed else 'FAIL'} {name}: {note}")
            failures += 0 if passed else 1
    print(f"{len(entries) - failures} of {len(entries)} fixtures match their expectation")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
