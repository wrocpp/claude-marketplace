#!/bin/sh
# Build with coverage, run the tests, write a gcovr JSON report and score it with crap.py.
#
# usage: coverage.sh [-c CONFIG] [-p PRESET] [-g GCOV] [-j JSON] [-b BUILD_DIR] [--no-gate]
# Run from the project root. Settings come from the options, then from the "coverage"
# section of .claude/cpp-quality-gates.json (preset, build_dir, gcov, filters), then the defaults:
# preset "coverage", build_dir "build/<preset>", gcov "gcov" (use gcov-N beside g++-N; Apple clang needs a gcc), filters = crap roots.
# Every value that reaches a command line is validated by qg_config.py (a token or a relative
# path of [A-Za-z0-9_./-]); an invalid one stops the script with exit 2. No value goes through eval.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
config=.claude/cpp-quality-gates.json
gate=1
preset= gcov= json= bindir=
cfg() { python3 "$here/qg_config.py" "$@"; }
while [ $# -gt 0 ]; do
  [ $# -ge 2 ] || [ "$1" = --no-gate ] || { echo "coverage.sh: $1 needs a value" >&2; exit 2; }
  case $1 in
    -c) cfg check path "$2"; config=$2; shift 2 ;;
    -p) cfg check token "$2"; preset=$2; shift 2 ;;
    -g) cfg check token "$2"; gcov=$2; shift 2 ;;
    -j) cfg check path "$2"; json=$2; shift 2 ;;
    -b) cfg check path "$2"; bindir=$2; shift 2 ;;
    --no-gate) gate=0; shift ;;
    *) echo "coverage.sh: unknown option" >&2; exit 2 ;;
  esac
done
QG_CONFIG=$config
export QG_CONFIG
[ -n "$preset" ] || preset=$(cfg coverage preset coverage token)
[ -n "$gcov" ] || gcov=$(cfg coverage gcov gcov token)
[ -n "$bindir" ] || bindir=$(cfg coverage build_dir "build/$preset" path)
roots=$(cfg crap roots src paths)
filters=$(cfg coverage filters "$(printf '%s' "$roots" | tr '\n' ' ')" paths)

cmake --preset "$preset" >/dev/null
cmake --build --preset "$preset"
find "$bindir" -name '*.gcda' -delete
ctest --preset "$preset" --output-on-failure
[ -n "$json" ] || json=$bindir/cov.json

set --
while IFS= read -r filter; do
  set -- "$@" --filter "$filter"
done <<FILTERS
$filters
FILTERS
# -r is the physical path: GCC records real paths, and /var/... on macOS is /private/var/...
gcovr --gcov-executable "$gcov" -r "$(pwd -P)" "$@" --gcov-ignore-errors=no_working_dir_found --json "$json" "$bindir"
[ "$gate" -eq 0 ] || exec python3 "$here/crap.py" "$json" --config "$config"
