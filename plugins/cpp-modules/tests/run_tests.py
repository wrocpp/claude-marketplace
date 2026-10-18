#!/usr/bin/env python3
"""Run the cpp-modules checks: the gate finder, the starter template and every trap fixture.

A missing GCC 16, CMake or Ninja prints `SKIP <thing>`; with WROCPP_CI=1 it is a failure.
Environment: CXX and CMAKE pick the tools, WROCPP_VENV is the virtual environment tests/setup.sh made.
"""
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
PLUGIN = HERE.parent
STARTER = PLUGIN / "templates" / "modules-starter"
GATE_FINDER = PLUGIN / "scripts" / "find_import_std_gate.py"
GATE_TABLE = STARTER / "cmake" / "ImportStdGate.cmake"
DEFAULT_VENV = "/opt/wrocpp-venv"
MINIMUM_GCC_MAJOR = 16
MINIMUM_CMAKE = (4, 0, 3)
EXTRA_CMAKE = ((3, 31, 10),)
GREETING = "Hello, Wro.cpp!"
STEP_TIMEOUT_SECONDS = 900
STRICT = os.environ.get("WROCPP_CI") == "1"


def run(arguments, cwd=None, extra_env=None):
    environment = {**os.environ, **(extra_env or {})}
    try:
        result = subprocess.run(arguments, cwd=cwd, env=environment, capture_output=True, text=True, timeout=STEP_TIMEOUT_SECONDS)
    except (OSError, subprocess.TimeoutExpired) as error:
        return 127, str(error)
    return result.returncode, result.stdout + result.stderr


def missing(thing):
    print(f"{'FAIL' if STRICT else 'SKIP'} {thing}")
    return 1 if STRICT else 0


def gcc_major(compiler):
    code, output = run([compiler, "-dumpfullversion"])
    found = re.match(r"(\d+)\.", output) if code == 0 else None
    return int(found.group(1)) if found else 0


def find_compiler():
    candidates = [os.environ.get("CXX"), "g++-16", "g++"]
    for candidate in filter(None, candidates):
        path = shutil.which(candidate)
        if path and gcc_major(path) >= MINIMUM_GCC_MAJOR:
            return path
    return None


def cmake_version(cmake):
    code, output = run([cmake, "--version"])
    found = re.match(r"cmake version (\d+)\.(\d+)\.(\d+)", output) if code == 0 else None
    return tuple(int(part) for part in found.groups()) if found else (0, 0, 0)


def find_cmake():
    venv = os.environ.get("WROCPP_VENV", DEFAULT_VENV)
    candidates = [os.environ.get("CMAKE"), f"{venv}/bin/cmake", "cmake"]
    for candidate in filter(None, candidates):
        path = shutil.which(candidate)
        version = cmake_version(path) if path else (0, 0, 0)
        if path and (version >= MINIMUM_CMAKE or version in EXTRA_CMAKE):
            return path
    return None


def gate_finder(cmake, cxx):
    code, output = run([sys.executable, "-I", str(GATE_FINDER), "--cmake", cmake, "--cxx", cxx])
    gate = output.strip()
    table = GATE_TABLE.read_text(encoding="utf-8")
    if code != 0 or gate not in table:
        print(f"FAIL gate finder: it printed {gate!r} for CMake {cmake_version(cmake)}; the table in cmake/ImportStdGate.cmake has no such gate")
        return 1
    print(f"PASS gate finder: {gate} is in the starter's table")
    return 0


def starter(cmake, cxx):
    failures = 0
    with tempfile.TemporaryDirectory(prefix="wrocpp-starter-") as directory:
        copy = pathlib.Path(directory) / "modules-starter"
        shutil.copytree(STARTER, copy)
        environment = {"CXX": cxx, "PATH": f"{pathlib.Path(cmake).parent}{os.pathsep}{os.environ['PATH']}"}
        for preset in ("host", "asan"):
            steps = ([cmake, "--preset", preset], [cmake, "--build", "--preset", preset], ["ctest", "--preset", preset])
            for step in steps:
                code, output = run(list(step), cwd=copy, extra_env=environment)
                if code != 0:
                    print(f"FAIL starter {preset}: {' '.join(step[:3])}\n{output[-2000:]}")
                    failures += 1
                    break
            else:
                print(f"PASS starter {preset}: configure, build and ctest")
        code, output = run([str(copy / "build" / "host" / "starter"), "Wro.cpp"])
        if code != 0 or output.strip() != GREETING:
            print(f"FAIL starter output: {output!r}")
            failures += 1
        else:
            print(f"PASS starter output: {GREETING}")
    return failures


def main():
    cxx = find_compiler()
    if cxx is None:
        return missing(f"GCC {MINIMUM_GCC_MAJOR} (set CXX)")
    cmake = find_cmake()
    if cmake is None:
        return missing("CMake 4.0.3 or newer, or 3.31.10 (tests/setup.sh installs one; set CMAKE)")
    if shutil.which("ninja") is None:
        return missing("ninja")
    print(f"compiler {cxx}, cmake {cmake} {'.'.join(map(str, cmake_version(cmake)))}")
    failures = gate_finder(cmake, cxx)
    failures += starter(cmake, cxx)
    code, output = run([sys.executable, "-I", str(HERE / "run_fixtures.py"), "--cmake", cmake, "--cxx", cxx])
    print(output.rstrip())
    return 1 if failures or code != 0 else 0


if __name__ == "__main__":
    sys.exit(main())
