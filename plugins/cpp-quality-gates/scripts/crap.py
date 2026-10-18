#!/usr/bin/env python3
"""CRAP gate: score every function in ROOTS from lizard complexity and a gcovr JSON report.

usage: crap.py COVERAGE_JSON [ROOTS ...] [--max N] [--top N] [--missing zero|covered] [--config FILE]

Exit 0 when no function is above --max, 1 when some are, 2 when lizard is missing.
ROOTS and --max default to the "crap" section of .claude/cpp-quality-gates.json.
"""
import argparse
import json
import os
import pathlib
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qg_config

DEFAULT_MAX = 8.0
DEFAULT_SUFFIXES = (".cpp", ".cc", ".cxx", ".cppm", ".ixx", ".hpp", ".h")


def crap(complexity, covered_fraction):
    return complexity**2 * (1 - covered_fraction) ** 3 + complexity


def coverage_by_line(report):
    table = {}
    for entry in report["files"]:
        hits = table.setdefault(os.path.normpath(entry["file"]), {})
        for line in entry["lines"]:
            number = line["line_number"]
            hits[number] = hits.get(number, False) or line["count"] > 0
    return table


def functions_of(lizard, path):
    return lizard.analyze_file.analyze_source_code(str(path.with_suffix(".cpp")), path.read_text(encoding="utf-8", errors="replace")).function_list


def covered_fraction(function, lines):
    inside = [hit for number, hit in lines.items() if function.start_line <= number <= function.end_line]
    return sum(inside) / len(inside) if inside else 1.0


def score_file(lizard, path, lines):
    for function in functions_of(lizard, path):
        fraction = covered_fraction(function, lines)
        yield function.name, function.start_line, function.cyclomatic_complexity, fraction, crap(function.cyclomatic_complexity, fraction)


def source_files(roots, suffixes):
    for root in roots:
        for path in sorted(pathlib.Path(root).rglob("*")):
            if path.suffix in suffixes and path.is_file():
                yield path


def parse(argv):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("coverage_json")
    parser.add_argument("roots", nargs="*")
    parser.add_argument("--max", type=float)
    parser.add_argument("--top", type=int, default=0, help="also print the N worst functions, offenders or not")
    parser.add_argument("--missing", choices=("zero", "covered"), default="zero", help="coverage assumed for a file the report does not mention")
    parser.add_argument("--config")
    return parser.parse_args(argv)


def main(argv):
    arguments = parse(argv)
    try:
        import lizard
    except ImportError:
        print("crap: the lizard module is missing (pip install lizard)", file=sys.stderr)
        return 2
    roots = arguments.roots or qg_config.get_list("crap", "roots", ["src"], "path", arguments.config)
    limit = arguments.max if arguments.max is not None else qg_config.get("crap", "max", DEFAULT_MAX, "number", arguments.config)
    suffixes = tuple(qg_config.get_list("crap", "suffixes", list(DEFAULT_SUFFIXES), "suffix", arguments.config))
    report = coverage_by_line(json.loads(pathlib.Path(arguments.coverage_json).read_text(encoding="utf-8")))
    scored = []
    for path in source_files(roots, suffixes):
        known = os.path.normpath(path.as_posix()) in report
        lines = report.get(os.path.normpath(path.as_posix()), {})
        for name, start, complexity, fraction, score in score_file(lizard, path, lines):
            if not known and arguments.missing == "zero":
                fraction, score = 0.0, crap(complexity, 0.0)
            scored.append((score, path.as_posix(), start, name, complexity, fraction))
    offenders = [row for row in scored if row[0] > limit]
    shown = sorted(scored, reverse=True)[: arguments.top] if arguments.top else sorted(offenders, reverse=True)
    for score, path, start, name, complexity, fraction in shown:
        print(f"CRAP {score:6.1f}  CC {complexity:2d}  cov {fraction:4.0%}  {qg_config.show_path(path)}:{start}  {qg_config.show_name(name)}")
    print(f"{len(scored)} functions, {len(offenders)} above CRAP {limit:g}")
    return 1 if offenders else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
