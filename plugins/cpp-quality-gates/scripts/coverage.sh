#!/bin/sh
# Build with coverage, run the tests, write a gcovr JSON report and score it with crap.py.
#
# usage: coverage.sh [-c CONFIG] [-p PRESET] [-g GCOV] [-j JSON] [-b BUILD_DIR] [--no-gate]
# Run from the project root. Settings come from the options, then from the "coverage"
# section of .claude/cpp-quality-gates.json (preset, build_dir, gcov, filters), then the defaults:
# preset "coverage", build_dir "build/<preset>", gcov "gcov" (use gcov-N beside g++-N; Apple clang needs a gcc), filters = crap roots.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
config=.claude/cpp-quality-gates.json
gate=1
preset= gcov= json= bindir=
while [ $# -gt 0 ]; do
  case $1 in
    -c) config=$2; shift 2 ;;
    -p) preset=$2; shift 2 ;;
    -g) gcov=$2; shift 2 ;;
    -j) json=$2; shift 2 ;;
    -b) bindir=$2; shift 2 ;;
    --no-gate) gate=0; shift ;;
    *) echo "coverage.sh: unknown option $1" >&2; exit 2 ;;
  esac
done
QG_CONFIG=$config
export QG_CONFIG
cfg() { python3 "$here/qg_config.py" "$@"; }
[ -n "$preset" ] || preset=$(cfg coverage preset coverage token)
[ -n "$gcov" ] || gcov=$(cfg coverage gcov gcov token)
roots=$(cfg crap roots src paths)
filters=$(cfg coverage filters "$roots" paths)

bindir=${bindir:-$(cfg coverage build_dir "build/$preset" path)}
cmake --preset "$preset" >/dev/null
cmake --build --preset "$preset"
find "$bindir" -name '*.gcda' -delete
ctest --preset "$preset" --output-on-failure
[ -n "$json" ] || json=$bindir/cov.json
filter_args=
for f in $filters; do filter_args="$filter_args --filter $f"; done
# shellcheck disable=SC2086
# -r is the physical path: GCC records real paths, and /var/... on macOS is /private/var/...
gcovr --gcov-executable "$gcov" -r "$(pwd -P)" $filter_args --gcov-ignore-errors=no_working_dir_found --json "$json" "$bindir"
[ "$gate" -eq 0 ] || exec python3 "$here/crap.py" "$json" $roots --config "$config"
