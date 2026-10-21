#!/usr/bin/env python3
"""Run two or more benchmark commands alternately and print median (min-max) per measurement.

    alternate.py [--runs N] [--balance] [--ignore-field K] LABEL=COMMAND LABEL=COMMAND ...

Each COMMAND is split with shlex and run without a shell; its stdout carries one measurement per line,
as plain CSV with no header:

    name,detail,...,value

The last field is a number. Every other field except the one named by --ignore-field (0-based; use it
when a field holds the variant name) forms the key. A line that does not end in a number, and a line
that starts with '#', is ignored. A key must appear in every run of every command to be reported.

Runs alternate A B A B ... so a slow drift of the machine hits every design alike. --balance reverses
the order on every second run (A B, B A, A B ...), which also cancels a "second one is warm" effect.
The load average is read before the first and after the last run: a figure measured on a busy machine
is a hint, not a result.
"""
import argparse
import os
import shlex
import statistics
import subprocess
import sys

DEFAULT_RUNS = 7
RUN_DIGITS = 1
COMMENT = "#"
FIELD_SEPARATOR = ","
MINIMUM_DESIGNS = 2


def parse_measurements(text, ignore_field=None):
    """Return {key tuple: value} for the lines of one run."""
    found = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(COMMENT):
            continue
        fields = line.split(FIELD_SEPARATOR)
        try:
            value = float(fields[-1])
        except ValueError:
            continue
        key = [f.strip() for f in fields[:-1]]
        if ignore_field is not None and ignore_field < len(key):
            del key[ignore_field]
        found[tuple(key)] = value
    return found


def run_order(labels, run_index, balance):
    """The labels in the order they run for the run with this index."""
    reverse = balance and run_index % 2 == 1
    return list(reversed(labels)) if reverse else list(labels)


def run_command(argv):
    return subprocess.run(argv, check=True, stdout=subprocess.PIPE, text=True).stdout


def collect(commands, runs, balance, ignore_field, runner=run_command):
    """Run every command `runs` times, alternating. Returns (samples, order).

    samples[label][key] is the list of values, one per run; order is the labels in the order they ran.
    """
    labels = list(commands)
    samples = {label: {} for label in labels}
    order = []
    for index in range(runs):
        for label in run_order(labels, index, balance):
            order.append(label)
            found = parse_measurements(runner(commands[label]), ignore_field)
            for key, value in found.items():
                samples[label].setdefault(key, []).append(value)
    return samples, order


def common_keys(samples, runs):
    """Keys that every design reported in every run, in a stable order."""
    per_label = [{k for k, values in table.items() if len(values) == runs} for table in samples.values()]
    return sorted(set.intersection(*per_label)) if per_label else []


def summary(values):
    return statistics.median(values), min(values), max(values)


def cell(values):
    middle, low, high = summary(values)
    return f"{middle:.{RUN_DIGITS}f} ({low:.{RUN_DIGITS}f}-{high:.{RUN_DIGITS}f})"


def ratio(values, baseline):
    return statistics.median(values) / statistics.median(baseline)


def table_rows(samples, runs):
    labels = list(samples)
    first = labels[0]
    for key in common_keys(samples, runs):
        cells = [cell(samples[label][key]) for label in labels]
        ratios = [f"{ratio(samples[label][key], samples[first][key]):.2f}" for label in labels[1:]]
        yield [FIELD_SEPARATOR.join(key)] + cells + ratios


def header(labels):
    first = labels[0]
    return ["key"] + labels + [f"{label}/{first}" for label in labels[1:]]


def render(samples, runs):
    labels = list(samples)
    rows = [header(labels)] + list(table_rows(samples, runs))
    lines = ["| " + " | ".join(row) + " |" for row in rows]
    lines.insert(1, "|" + "---|" * len(rows[0]))
    return "\n".join(lines)


def parse_designs(specs):
    commands = {}
    for spec in specs:
        label, separator, command = spec.partition("=")
        if not separator or not label or not command.strip() or label in commands:
            raise ValueError(f"expected a unique LABEL=COMMAND, got {spec!r}")
        commands[label] = shlex.split(command)
    if len(commands) < MINIMUM_DESIGNS:
        raise ValueError("give at least two LABEL=COMMAND designs to compare")
    return commands


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--runs", type=int, default=DEFAULT_RUNS)
    parser.add_argument("--balance", action="store_true", help="reverse the order on every second run")
    parser.add_argument("--ignore-field", type=int, default=None, metavar="K", help="0-based field to leave out of the key")
    parser.add_argument("designs", nargs="+", metavar="LABEL=COMMAND")
    args = parser.parse_args(argv)
    if args.runs < 1:
        parser.error("--runs must be at least 1")
    try:
        args.commands = parse_designs(args.designs)
    except ValueError as problem:
        parser.error(str(problem))
    return args


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    before = os.getloadavg()[0]
    samples, order = collect(args.commands, args.runs, args.balance, args.ignore_field)
    after = os.getloadavg()[0]
    print(f"# runs {args.runs}, order {' '.join(order)}, load before {before:.2f} after {after:.2f}")
    print("# median (min-max); a difference inside the spread, or under the cost of one call, is not a result")
    print(render(samples, args.runs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
