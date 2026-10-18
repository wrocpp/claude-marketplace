#!/usr/bin/env python3
"""Compile every fixture with every available compiler and compare with expectations.json.

An outcome is one of: accept (exit 0, no warning), warn (exit 0, a warning), reject (non-zero exit).
Exit status: 0 when every observed outcome matches, 1 on a mismatch or a missing required compiler.
"""
import argparse
import glob
import json
import os
import pathlib
import platform
import re
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"
EXPECTATIONS_NAME = "expectations.json"
DEFAULT_FLAGS = ["-std=c++23", "-Wall", "-Wextra", "-O2", "-c"]
FAMILIES = ("gcc", "clang", "apple-clang")
CI_REQUIRED = ("gcc", "clang")
COMPILE_TIMEOUT_SECONDS = 120
VERSION_TIMEOUT_SECONDS = 20
BREW_LLVM_GLOB = "/opt/homebrew/opt/llvm*/bin/clang++"
PATH_CANDIDATES = ("g++-16", "g++-15", "g++", "clang++", "/usr/bin/clang++")
COMPILERS_ENV = "WROCPP_COMPILERS"
CI_ENV = "WROCPP_CI"
VERSION = re.compile(r"(\d+)\.\d+(?:\.\d+)?")


class Compiler:
    def __init__(self, path, family, major, banner):
        self.path = path
        self.family = family
        self.major = major
        self.banner = banner
        self.stdlib = detect_stdlib(path)

    @property
    def ident(self):
        return f"{self.family}-{self.major}"

    def keys(self):
        return (self.ident, f"{self.family}+{self.stdlib}", self.family)


def detect_stdlib(path):
    probe_source = "#include <version>\n#if defined(_LIBCPP_VERSION)\n#error libc++\n#elif defined(__GLIBCXX__)\n#error libstdc++\n#endif\n"
    try:
        result = subprocess.run([path, "-std=c++20", "-x", "c++", "-fsyntax-only", "-"], input=probe_source, capture_output=True, text=True, timeout=VERSION_TIMEOUT_SECONDS)
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    for name in ("libc++", "libstdc++"):
        if f"error: {name}" in result.stderr or f"#error {name}" in result.stderr:
            return name
    return "unknown"


def probe(path):
    try:
        out = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=VERSION_TIMEOUT_SECONDS).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    first = out.splitlines()[0] if out else ""
    found = VERSION.search(first)
    if not found:
        return None
    if "Apple clang" in first:
        family = "apple-clang"
    elif "clang" in first:
        family = "clang"
    elif "GCC" in first or "g++" in first:
        family = "gcc"
    else:
        return None
    return Compiler(path, family, int(found.group(1)), first.strip())


def discover():
    explicit = os.environ.get(COMPILERS_ENV)
    if explicit:
        candidates = explicit.split()
    else:
        candidates = [shutil.which(name) or "" for name in PATH_CANDIDATES] + sorted(glob.glob(BREW_LLVM_GLOB))
    found = {}
    for candidate in candidates:
        if not candidate or candidate.startswith("-") or ".." in pathlib.PurePath(candidate).parts:
            continue
        compiler = probe(candidate)
        if compiler is not None:
            found.setdefault((compiler.ident, compiler.banner), compiler)
    return sorted(found.values(), key=lambda c: (c.family, c.major))


def classify(compiler, source, flags):
    with tempfile.TemporaryDirectory() as scratch:
        command = [compiler.path, *flags, str(source), "-o", os.path.join(scratch, "out.o")]
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=COMPILE_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            return "reject", "timeout"
    diagnostics = result.stderr
    if result.returncode != 0:
        return "reject", diagnostics
    if re.search(r"\bwarning:", diagnostics):
        return "warn", diagnostics
    return "accept", diagnostics


def expected_for(entry, compiler):
    for key in (*compiler.keys(), "all"):
        if key in entry:
            return entry[key]
    return None


def required_families():
    wanted = list(CI_REQUIRED)
    if platform.system() == "Darwin":
        wanted.append("apple-clang")
    return wanted


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--measure", action="store_true", help="print observed outcomes as JSON, compare nothing")
    parser.add_argument("--table", action="store_true", help="print a markdown table of the results")
    parser.add_argument("--dir", type=pathlib.Path, default=FIXTURES, help="fixture directory holding expectations.json")
    parser.add_argument("--include", action="append", default=[], help="extra include directory (repeatable)")
    args = parser.parse_args()

    fixtures_dir = args.dir.resolve()
    expectations = fixtures_dir / EXPECTATIONS_NAME
    fixtures = json.loads(expectations.read_text(encoding="utf-8")) if expectations.exists() else {}
    extra_flags = [f"-I{directory}" for directory in args.include]
    compilers = discover()
    failures = 0
    ci = os.environ.get(CI_ENV) == "1"
    present = {c.family for c in compilers}
    for family in required_families():
        if family not in present:
            print(f"{'FAIL' if ci else 'SKIP'} {family}: no such compiler found")
            failures += 1 if ci else 0
    if not compilers:
        return 1 if ci else 0

    names = sorted(p.name for p in fixtures_dir.glob("*.cpp"))
    entries = dict(fixtures)
    for name in names:
        entries.setdefault(name, {})
    rows = {}
    for key, entry in sorted(entries.items()):
        source = fixtures_dir / entry.get("source", key)
        if not source.exists():
            print(f"FAIL {key}: source {source.name} is missing")
            failures += 1
            continue
        flags = [*entry.get("flags", DEFAULT_FLAGS), *extra_flags]
        for compiler in compilers:
            if expected_for(entry, compiler) == "skip":
                rows.setdefault(key, {})[compiler.ident] = "skip"
                continue
            observed, diagnostics = classify(compiler, source, flags)
            rows.setdefault(key, {})[compiler.ident] = observed
            if args.measure:
                continue
            want = expected_for(entry, compiler)
            if want is None:
                print(f"FAIL {key} [{compiler.ident}]: no expectation (observed {observed})")
                failures += 1
            elif want != observed:
                print(f"FAIL {key} [{compiler.ident}]: expected {want}, observed {observed}")
                print("    " + "\n    ".join(diagnostics.strip().splitlines()[:6]))
                failures += 1
    unknown = [k for k in fixtures if not (fixtures_dir / fixtures[k].get("source", k)).exists()]
    for key in unknown:
        print(f"FAIL {key}: listed in expectations.json but the source is missing")
        failures += 1

    if args.measure:
        print(json.dumps(rows, indent=2, sort_keys=True))
        return 0
    print_table(compilers, rows)
    print(f"fixtures: {len(rows)}, compilers: {len(compilers)}, failures: {failures}")
    return 1 if failures else 0


def print_table(compilers, rows):
    idents = [c.ident for c in compilers]
    print("compilers:")
    for compiler in compilers:
        print(f"  {compiler.ident} ({compiler.stdlib}): {compiler.banner}")
    width = max(len(k) for k in rows) if rows else 10
    print(f"{'fixture'.ljust(width)}  " + "  ".join(i.ljust(11) for i in idents))
    for key in sorted(rows):
        print(f"{key.ljust(width)}  " + "  ".join(rows[key].get(i, "-").ljust(11) for i in idents))


if __name__ == "__main__":
    sys.exit(main())
