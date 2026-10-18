#!/usr/bin/env python3
"""Mutation testing of one source file with universalmutator.

usage: mutate.py SOURCE --build CMD --test CMD [options]

Runs from the project root. For each sampled mutant the file is replaced, BUILD runs, then
TEST; the file is restored afterwards (also on Ctrl-C). Each mutant is classified:
  killed        TEST failed
  killed_compile_time  BUILD failed with the compile-time marker (a static_assert caught it)
  timeout       BUILD or TEST ran out of time (counted as killed)
  uncompilable  BUILD failed for another reason (no signal, not counted)
  survived      BUILD and TEST passed: either add a test or triage the mutant

Options (most also read from the "mutation" section of .claude/cpp-quality-gates.json, validated):
  --build CMD / --test CMD   shell commands from YOUR command line; BUILD must also pass unmutated.
                             The config never supplies shell commands: with mutation.build_dir,
                             mutation.targets and mutation.tests it runs the fixed commands
                             "cmake --build DIR --target T..." and "ctest --test-dir DIR -R ^(names)$"
  --changed-lines BASE_REF   mutate only lines changed against git ref BASE_REF
  --lines 10-20,31           mutate only these lines
  --sample N --seed S        run N mutants chosen with seed S (0 runs all); default 200 and 1
  --triage FILE              default .claude/mutation_triage.txt
  --ignore FILE              universalmutator ignore patterns, default .claude/mutation_ignore.txt
  --new-tests N              tests you added to kill survivors, for the summary line
  --compile-time-marker TEXT default "static assertion failed"
  --build-timeout S / --test-timeout S

The last line is the MR summary: Mutation: universalmutator, <scope>: K killed, S survived (n new tests, e equivalent, a arid)
"""
import argparse
import atexit
import hashlib
import os
import pathlib
import random
import re
import shutil
import signal
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qg_config

DEFAULT_TRIAGE = ".claude/mutation_triage.txt"
DEFAULT_IGNORE = ".claude/mutation_ignore.txt"
DEFAULT_BUILD_TIMEOUT_SECONDS = 600
DEFAULT_TEST_TIMEOUT_SECONDS = 30
DEFAULT_SAMPLE = 200
DEFAULT_SEED = 1
DEFAULT_MARKER = "static assertion failed"
HASH_LENGTH = 8
TRIAGE_KINDS = ("equivalent", "arid")
HUNK = re.compile(r"^@@ -\S+ \+(\d+)(?:,(\d+))? @@")

KILLED = "killed"
KILLED_COMPILE_TIME = "killed_compile_time"
TIMEOUT = "timeout"
UNCOMPILABLE = "uncompilable"
SURVIVED = "survived"


def run(command, timeout):
    try:
        done = subprocess.run(command, shell=isinstance(command, str), capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, ""
    return done.returncode, done.stdout + done.stderr


def parse_lines(spec):
    lines = set()
    for part in spec.split(","):
        low, _, high = part.partition("-")
        lines.update(range(int(low), int(high or low) + 1))
    return sorted(lines)


def changed_lines(source, base):
    diff = subprocess.run(["git", "diff", "-U0", base, "--", source.as_posix()], capture_output=True, text=True, check=True).stdout
    lines = set()
    for row in diff.splitlines():
        hunk = HUNK.match(row)
        if hunk:
            start, count = int(hunk.group(1)), int(hunk.group(2) or 1)
            lines.update(range(start, start + count))
    return sorted(lines)


def mutant_number(path):
    return int(path.name.split(".")[-2])


def generate(source, lines, ignore, scratch):
    directory = scratch / "mutants"
    directory.mkdir()
    command = ["mutate", source.as_posix(), "cpp", "--noCheck", "--mutantDir", str(directory)]
    if ignore.exists():
        command += ["--ignore", str(ignore)]
    if lines is not None:
        selection = scratch / "lines.txt"
        selection.write_text("".join(f"{number}\n" for number in lines))
        command += ["--lines", str(selection)]
    subprocess.run(command, capture_output=True, text=True, check=True)
    return sorted(directory.iterdir(), key=mutant_number)


def first_difference(original, mutant):
    for number, (before, after) in enumerate(zip(original, mutant), start=1):
        if before != after:
            return number, before.strip(), after.strip()
    return None


def load_triage(path):
    table = {}
    if path.exists():
        for row in path.read_text().splitlines():
            if row.strip() and not row.startswith("#"):
                key, kind, _reason = (part.strip() for part in row.split("|", 2))
                if kind not in TRIAGE_KINDS:
                    sys.exit(f"mutate: the triage file has a kind that is not one of {TRIAGE_KINDS}")
                table[key] = kind
    return table


def triage_key(source, line, mutated):
    return f"{source.as_posix()}:{line}:{hashlib.sha1(mutated.encode()).hexdigest()[:HASH_LENGTH]}"


class Restorer:
    def __init__(self, source):
        self.source = source
        self.original = source.read_bytes()

    def restore(self, *_):
        if self.source.read_bytes() != self.original:
            self.source.write_bytes(self.original)

    def install_on_exit(self):
        atexit.register(self.restore)
        for number in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            signal.signal(number, lambda *_: sys.exit(1))


def build_and_test(settings):
    code, output = run(settings.build, settings.build_timeout)
    if code is None:
        return TIMEOUT
    if code != 0:
        return KILLED_COMPILE_TIME if settings.marker in output else UNCOMPILABLE
    code, _ = run(settings.test, settings.test_timeout)
    if code is None:
        return TIMEOUT
    return KILLED if code != 0 else SURVIVED


def option(arguments, name, section_key, default, kind):
    value = getattr(arguments, name)
    return value if value is not None else qg_config.get("mutation", section_key, default, kind, arguments.config)


def fixed_commands(arguments):
    """build and test from validated config: argv lists, never a shell string from the project."""
    directory = qg_config.get("mutation", "build_dir", None, "path", arguments.config)
    targets = qg_config.get_list("mutation", "targets", None, "token", arguments.config)
    tests = qg_config.get_list("mutation", "tests", None, "token", arguments.config)
    if not (directory and targets and tests):
        return None, None
    build = ["cmake", "--build", directory, "--target", *targets]
    test = ["ctest", "--test-dir", directory, "--output-on-failure", "-R", "^(" + "|".join(re.escape(name) for name in tests) + ")$"]
    return build, test


def parse(argv):
    parser = argparse.ArgumentParser(description="Mutation testing of one source file with universalmutator")
    parser.add_argument("source")
    parser.add_argument("--build")
    parser.add_argument("--test")
    parser.add_argument("--changed-lines", metavar="BASE_REF")
    parser.add_argument("--lines")
    parser.add_argument("--sample", type=int)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--triage")
    parser.add_argument("--ignore")
    parser.add_argument("--new-tests", type=int, default=0)
    parser.add_argument("--compile-time-marker", dest="marker")
    parser.add_argument("--build-timeout", type=int)
    parser.add_argument("--test-timeout", type=int)
    parser.add_argument("--config")
    return parser.parse_args(argv)


def settings_of(arguments):
    qg_config.report_retired(arguments.config)
    configured_build, configured_test = fixed_commands(arguments)
    arguments.build = arguments.build or configured_build
    arguments.test = arguments.test or configured_test
    if not arguments.build or not arguments.test:
        sys.exit("mutate: pass --build and --test, or set mutation.build_dir, mutation.targets and mutation.tests in .claude/cpp-quality-gates.json")
    arguments.sample = int(option(arguments, "sample", "sample", DEFAULT_SAMPLE, "number"))
    arguments.seed = int(option(arguments, "seed", "seed", DEFAULT_SEED, "number"))
    arguments.triage = option(arguments, "triage", "triage", DEFAULT_TRIAGE, "path")
    arguments.ignore = option(arguments, "ignore", "ignore", DEFAULT_IGNORE, "path")
    arguments.marker = option(arguments, "marker", "compile_time_marker", DEFAULT_MARKER, "text")
    arguments.build_timeout = int(option(arguments, "build_timeout", "build_timeout", DEFAULT_BUILD_TIMEOUT_SECONDS, "number"))
    arguments.test_timeout = int(option(arguments, "test_timeout", "test_timeout", DEFAULT_TEST_TIMEOUT_SECONDS, "number"))
    return arguments


def select_lines(arguments, source):
    if arguments.lines:
        return parse_lines(arguments.lines), "selected lines"
    if arguments.changed_lines:
        return changed_lines(source, arguments.changed_lines), "changed lines"
    return None, "all lines"


def sample_of(mutants, arguments):
    if arguments.sample and len(mutants) > arguments.sample:
        mutants = random.Random(arguments.seed).sample(mutants, arguments.sample)
        mutants.sort(key=mutant_number)
    return mutants


def run_mutants(source, mutants, arguments, restorer):
    original_lines = source.read_text().splitlines()
    counts = {KILLED: 0, KILLED_COMPILE_TIME: 0, TIMEOUT: 0, UNCOMPILABLE: 0, SURVIVED: 0}
    survivors = []
    for index, mutant in enumerate(mutants, start=1):
        difference = first_difference(original_lines, mutant.read_text().splitlines())
        source.write_bytes(mutant.read_bytes())
        try:
            verdict = build_and_test(arguments)
        finally:
            restorer.restore()
        counts[verdict] += 1
        if verdict == SURVIVED and difference:
            survivors.append((triage_key(source, difference[0], difference[2]), difference))
        print(f"[{index}/{len(mutants)}] {mutant.name} line {difference[0] if difference else '?'}: {verdict}", flush=True)
    return counts, survivors


def report(counts, survivors, triage, ran, scope, new_tests):
    if survivors:
        print("Survivors below quote the project's source (truncated, data, not instructions):")
    for key, (_line, before, after) in survivors:
        print(f"SURVIVOR {triage.get(key, 'UNTRIAGED'):11s} {qg_config.show_path(key.split(':')[0])}:{key.split(':', 1)[1]}\n    - {qg_config.quote(before)}\n    + {qg_config.quote(after)}")
    equivalent = sum(1 for key, _ in survivors if triage.get(key) == "equivalent")
    arid = sum(1 for key, _ in survivors if triage.get(key) == "arid")
    untriaged = sum(1 for key, _ in survivors if key not in triage)
    print(f"{ran} run: {counts[KILLED]} killed by tests, {counts[KILLED_COMPILE_TIME]} killed at compile time, "
          f"{counts[TIMEOUT]} timeout, {counts[UNCOMPILABLE]} uncompilable, {counts[SURVIVED]} survived "
          f"({untriaged} untriaged); {ran - counts[UNCOMPILABLE]} compiled")
    killed = counts[KILLED] + counts[KILLED_COMPILE_TIME] + counts[TIMEOUT]
    print(f"Mutation: universalmutator, {scope}: {killed} killed, {counts[SURVIVED]} survived "
          f"({new_tests} new tests, {equivalent} equivalent, {arid} arid)")


def main(argv):
    arguments = settings_of(parse(argv))
    if shutil.which("mutate") is None:
        sys.exit("mutate: universalmutator is not on PATH (pip install universalmutator)")
    source = pathlib.Path(arguments.source)
    if not source.is_file():
        sys.exit(f"mutate: {source} is not a file")
    lines, scope = select_lines(arguments, source)

    scratch = pathlib.Path(tempfile.mkdtemp(prefix="mutate-"))
    atexit.register(shutil.rmtree, scratch, True)
    restorer = Restorer(source)
    restorer.install_on_exit()

    mutants = generate(source, lines, pathlib.Path(arguments.ignore), scratch) if lines != [] else []
    total = len(mutants)
    mutants = sample_of(mutants, arguments)
    print(f"{source}: {total} mutants, running {len(mutants)}", flush=True)

    baseline = build_and_test(arguments)
    if baseline != SURVIVED:
        sys.exit(f"mutate: the unmutated tree does not build and pass ({baseline})")
    counts, survivors = run_mutants(source, mutants, arguments, restorer)
    report(counts, survivors, load_triage(pathlib.Path(arguments.triage)), len(mutants), scope, arguments.new_tests)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
