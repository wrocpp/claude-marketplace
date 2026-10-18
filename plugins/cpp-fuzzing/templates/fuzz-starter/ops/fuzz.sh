#!/bin/sh
# Time-boxed AFL++ campaign for one harness, inside the Docker image built from Dockerfile.fuzz.
#   ops/fuzz.sh <target> [seconds] [planted-bug]   target: the NAME of tests/harness_<NAME>.cpp
set -eu
root=$(cd "$(dirname "$0")/.." && pwd)
target=${1:?usage: ops/fuzz.sh <target> [seconds]}
seconds=${2:-60}
bug=${3:-none}
case $target in
  '' | [!a-z]* | *[!a-z_]*) echo "fuzz.sh: target must start with a lowercase letter and hold only lowercase letters and underscores" >&2; exit 2 ;;
esac
case $seconds in
  '' | *[!0-9]*) echo "fuzz.sh: seconds must be a number" >&2; exit 2 ;;
esac
case $bug in
  '' | [!a-z]* | *[!a-z_]*) echo "fuzz.sh: planted bug must start with a lowercase letter and hold only lowercase letters and underscores" >&2; exit 2 ;;
esac
[ -f "$root/tests/harness_$target.cpp" ] || { echo "fuzz.sh: no tests/harness_$target.cpp" >&2; exit 2; }

docker build -q -t fuzz-starter-afl -f "$root/ops/Dockerfile.fuzz" "$root/ops" >/dev/null
# AFL_USE_ASAN and AFL_USE_UBSAN instrument the target; leave FUZZ_STARTER_SANITIZE off here.
# Persistent mode: no @@, the harness reads each case from shared memory.
docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp \
  -e AFL_SKIP_CPUFREQ=1 -e AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES=1 -e AFL_NO_UI=1 \
  -e AFL_USE_ASAN=1 -e AFL_USE_UBSAN=1 \
  -e ASAN_OPTIONS=abort_on_error=1:symbolize=0:detect_leaks=0 -e UBSAN_OPTIONS=halt_on_error=1:abort_on_error=1 \
  -v "$root:/src" -w /src fuzz-starter-afl sh -c "
    rm -rf build/fuzz &&
    cmake -S . -B build/fuzz -G Ninja -DCMAKE_CXX_COMPILER=afl-g++-fast -DFUZZ_STARTER_PLANTED_BUG=$bug >/dev/null &&
    cmake --build build/fuzz --target fuzz_$target &&
    mkdir -p build/fuzz/findings/$target &&
    afl-fuzz -i corpus -o build/fuzz/findings/$target -m none -V $seconds -- build/fuzz/fuzz_$target;
    ls build/fuzz/findings/$target/default/crashes build/fuzz/findings/$target/default/hangs"
