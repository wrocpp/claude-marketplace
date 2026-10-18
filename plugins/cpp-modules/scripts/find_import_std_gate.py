#!/usr/bin/env python3
"""Find the CMAKE_EXPERIMENTAL_CXX_IMPORT_STD gate that makes `import std` build.

The gate is a UUID that changes between CMake releases, and a wrong one fails with the same
message as none. Every UUID embedded in the cmake executable is tried in a throwaway project.

Usage: find_import_std_gate.py [--cmake CMAKE] [--cxx COMPILER] [--std 23|26]
Prints the UUID, or `none` when CMake needs no gate or none works. Exit 0 found, 1 not found.
"""
import argparse
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

UUID = re.compile(rb"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
STEP_TIMEOUT_SECONDS = 300
PROJECT = """cmake_minimum_required(VERSION 3.30)
{gate}
project(probe LANGUAGES CXX)
set(CMAKE_CXX_STANDARD {std})
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_CXX_MODULE_STD ON)
add_executable(probe main.cpp)
"""
SOURCE = "import std;\nint main() { std::println(\"ok\"); }\n"


def run(arguments, cwd=None):
    return subprocess.run(arguments, cwd=cwd, capture_output=True, text=True, timeout=STEP_TIMEOUT_SECONDS)


def cmake_binary(cmake):
    with tempfile.TemporaryDirectory() as directory:
        script = pathlib.Path(directory) / "where.cmake"
        script.write_text("message(STATUS \"ROOT=${CMAKE_ROOT}\")\nmessage(STATUS \"COMMAND=${CMAKE_COMMAND}\")\n", encoding="utf-8")
        result = run([cmake, "-P", str(script)])
    output = result.stdout + result.stderr
    root = re.search(r"ROOT=(.+)", output)
    command = re.search(r"COMMAND=(.+)", output)
    beside_share = pathlib.Path(root.group(1).strip()) / ".." / ".." / "bin" / "cmake" if root else None
    if beside_share is not None and beside_share.is_file():
        return beside_share
    return pathlib.Path(command.group(1).strip()) if command else pathlib.Path(shutil.which(cmake) or cmake)


def candidates(cmake):
    data = cmake_binary(cmake).read_bytes()
    return sorted({match.decode("ascii") for match in UUID.findall(data)})


def builds(cmake, cxx, std, gate):
    with tempfile.TemporaryDirectory() as directory:
        root = pathlib.Path(directory)
        (root / "main.cpp").write_text(SOURCE, encoding="utf-8")
        line = f"set(CMAKE_EXPERIMENTAL_CXX_IMPORT_STD {gate})" if gate else ""
        (root / "CMakeLists.txt").write_text(PROJECT.format(gate=line, std=std), encoding="utf-8")
        configure = run([cmake, "-S", str(root), "-B", str(root / "b"), "-G", "Ninja", f"-DCMAKE_CXX_COMPILER={cxx}"])
        if configure.returncode != 0 or "CMake Error" in configure.stderr:
            return False
        return run([cmake, "--build", str(root / "b")]).returncode == 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cmake", default="cmake")
    parser.add_argument("--cxx", default="g++")
    parser.add_argument("--std", default="23", choices=("23", "26"))
    arguments = parser.parse_args()
    if builds(arguments.cmake, arguments.cxx, arguments.std, ""):
        print("none")
        return 0
    for gate in candidates(arguments.cmake):
        if builds(arguments.cmake, arguments.cxx, arguments.std, gate):
            print(gate)
            return 0
    print("none")
    return 1


if __name__ == "__main__":
    sys.exit(main())
