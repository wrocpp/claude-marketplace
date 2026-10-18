#!/bin/sh
# End-to-end test of cpp-quality-gates on the sample project in tests/sample.
# Exit 0 when every check passes. A missing tool is "SKIP"; with WROCPP_CI=1 a skip fails.
# Env: CXX (compiler for the CRAP and mutation steps; default g++-16, g++, c++ in that order)
set -u
here=$(cd "$(dirname "$0")" && pwd)
plugin=$(dirname "$here")
venv=${QG_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/wrocpp/cpp-quality-gates-venv}
[ -d "$venv/bin" ] && PATH="$venv/bin:$PATH"
export PATH

failures=0
pass() { echo "PASS $*"; }
fail() { echo "FAIL $*"; failures=$((failures + 1)); }
skip() { echo "SKIP $*"; [ "${WROCPP_CI:-0}" = 1 ] && failures=$((failures + 1)); }
need() { command -v "$1" >/dev/null 2>&1 || { skip "$2: $1 not installed (run tests/setup.sh)"; return 1; }; }
is_gcc() { "$1" --version 2>&1 | grep -q "Free Software Foundation"; }
gcov_for() { case $1 in *g++-[0-9]*) echo "gcov-${1##*g++-}" ;; *) echo gcov ;; esac; }

for tool in cmake ninja python3; do
  command -v "$tool" >/dev/null 2>&1 || { echo "FAIL $tool is required"; exit 1; }
done

# Work on a copy that mirrors the plugin layout, so the sample's relative includes resolve
# and nothing is written into the plugin.
work=$(cd "$(mktemp -d)" && pwd -P)
trap 'rm -rf "$work"' EXIT INT TERM
mkdir "$work/tests"
cp -R "$plugin/scripts" "$plugin/templates" "$work/"
cp -R "$here/sample" "$work/tests/"
sample=$work/tests/sample
scripts=$work/scripts

gcc_cxx=
for candidate in "${CXX:-}" g++-16 g++ c++; do
  [ -n "$candidate" ] && command -v "$candidate" >/dev/null 2>&1 && is_gcc "$candidate" && { gcc_cxx=$candidate; break; }
done
compilers=
seen=
for candidate in "${CXX:-}" g++-16 g++ clang++ /usr/bin/clang++; do
  [ -n "$candidate" ] && command -v "$candidate" >/dev/null 2>&1 || continue
  id=$("$candidate" --version 2>&1 | head -1)
  case $seen in *"$id"*) continue ;; esac
  seen="$seen|$id"
  compilers="$compilers $candidate"
done
echo "compilers:$compilers"
echo "gcc for coverage and mutation: ${gcc_cxx:-none}"
uname_s=$(uname -s)

# --- sanitizer matrix -------------------------------------------------------------------
rm -rf "$sample/build"
for cxx in $compilers; do
  tag=$(echo "$cxx" | tr '/+' '__')
  if ! (cd "$sample" && CXX=$cxx cmake --preset asan -B "build/asan-$tag" >/dev/null 2>"$work/configure.log"); then
    fail "asan configure with $cxx: $(tail -3 "$work/configure.log")"; continue
  fi
  if (cd "$sample" && cmake --build "build/asan-$tag" >"$work/build.log" 2>&1 && ctest --test-dir "build/asan-$tag" -L unit --output-on-failure >"$work/ctest.log" 2>&1); then
    pass "asan+ubsan builds and runs the unit tests with $cxx"
  else
    fail "asan+ubsan unit tests with $cxx"; tail -20 "$work/build.log" "$work/ctest.log"
  fi
  (cd "$sample" && cmake --build "build/asan-$tag" --target planted_heap_overflow planted_signed_overflow >"$work/planted.log" 2>&1) || { fail "planted targets with $cxx"; continue; }
  out=$("$sample/build/asan-$tag/planted_heap_overflow" 2>&1); code=$?
  if [ $code -ne 0 ] && echo "$out" | grep -q "AddressSanitizer: heap-buffer-overflow"; then pass "asan reports the planted heap overflow with $cxx"; else fail "asan missed the planted heap overflow with $cxx (rc=$code)"; fi
  out=$("$sample/build/asan-$tag/planted_signed_overflow" 2>&1); code=$?
  if [ $code -ne 0 ] && echo "$out" | grep -q "signed integer overflow"; then pass "ubsan reports the planted signed overflow with $cxx"; else fail "ubsan missed the planted signed overflow with $cxx (rc=$code)"; fi

  if [ "$uname_s" = Linux ]; then
    (cd "$sample" && cmake --build "build/asan-$tag" --target planted_leak >/dev/null 2>&1)
    out=$("$sample/build/asan-$tag/planted_leak" 2>&1); code=$?
    if [ $code -ne 0 ] && echo "$out" | grep -q "LeakSanitizer"; then pass "lsan reports the planted leak with $cxx"; else fail "lsan missed the planted leak with $cxx (rc=$code)"; fi
  else
    echo "NOTE lsan: not run on $uname_s (LeakSanitizer is Linux only; see skills/sanitizer-matrix)"
  fi

  if ! (cd "$sample" && CXX=$cxx cmake --preset tsan -B "build/tsan-$tag" >/dev/null 2>&1 && cmake --build "build/tsan-$tag" --target planted_race >"$work/tsan.log" 2>&1); then
    echo "NOTE tsan: $cxx cannot build with -fsanitize=thread on $uname_s (see skills/sanitizer-matrix)"
  else
    out=$("$sample/build/tsan-$tag/planted_race" 2>&1); code=$?
    if echo "$out" | grep -q "unable to disable ASLR"; then
      skip "tsan with $cxx: the sandbox blocks personality(ADDR_NO_RANDOMIZE); run with --security-opt seccomp=unconfined"
    elif [ $code -ne 0 ] && echo "$out" | grep -q "ThreadSanitizer: data race"; then pass "tsan reports the planted data race with $cxx"
    else fail "tsan missed the planted data race with $cxx (rc=$code): $(echo "$out" | head -3)"; fi
  fi
done

# --- CRAP pipeline ---------------------------------------------------------------------
if [ -z "$gcc_cxx" ]; then skip "crap pipeline: no GCC found"
elif need lizard crap && need gcovr crap; then
  out=$(cd "$sample" && CXX=$gcc_cxx "$scripts/coverage.sh" -g "$(gcov_for "$gcc_cxx")" 2>&1); code=$?
  echo "$out" | grep -E "^(CRAP|[0-9]+ functions)"
  [ $code -eq 1 ] && pass "coverage.sh exits 1 because the sample has offenders" || fail "coverage.sh exit code $code, wanted 1"
  echo "$out" | grep -q "^CRAP .*classify" && pass "crap reports classify (complex and under-tested)" || fail "crap did not report classify"
  echo "$out" | grep -q "^CRAP .*weekday" && pass "crap reports weekday (100% covered, CC 9)" || fail "crap did not report weekday"
  echo "$out" | grep -q "^CRAP .*clamp_add" && fail "crap reported clamp_add, a well-tested function" || pass "crap leaves clamp_add alone"
  echo "$out" | grep -q "^CRAP .*saturating_add" && fail "crap reported saturating_add" || pass "crap leaves saturating_add alone"
  top=$(cd "$sample" && python3 "$scripts/crap.py" build/coverage/cov.json src --top 1 --max 1000 | head -1)
  echo "$top" | grep -q "classify" && pass "crap --top lists the worst function first" || fail "crap --top: $top"
fi

# --- mutation harness ------------------------------------------------------------------
if [ -z "$gcc_cxx" ]; then skip "mutation harness: no GCC found"
elif need mutate mutation; then
  (cd "$sample" && CXX=$gcc_cxx cmake -S . -B build/mutate -G Ninja >/dev/null)
  out=$(cd "$sample" && python3 "$scripts/mutate.py" src/saturate.cpp --new-tests 0 2>&1); code=$?
  echo "$out" | tail -3
  [ $code -eq 0 ] && pass "mutate.py exits 0" || fail "mutate.py exit code $code"
  echo "$out" | grep -Eq "^Mutation: universalmutator, all lines: [1-9][0-9]* killed, 3 survived \(0 new tests, 3 equivalent, 0 arid\)$" \
    && pass "at least one mutant killed and the triage file marks all 3 survivors equivalent" || fail "mutation summary line"
  echo "$out" | grep -q "UNTRIAGED" && fail "an untriaged survivor remains" || pass "no untriaged survivor"
  echo "$out" | grep -q ": uncompilable" && pass "uncompilable mutants are classified apart" || fail "no uncompilable mutant seen"
  cmp -s "$sample/src/saturate.cpp" "$here/sample/src/saturate.cpp" && pass "the mutated file is restored" || fail "saturate.cpp was left modified"
  out=$(cd "$sample" && python3 "$scripts/mutate.py" src/saturate.cpp --triage /nonexistent --lines 5-6 2>&1 | tail -1)
  echo "$out" | grep -q "2 survived (0 new tests, 0 equivalent, 0 arid)" && pass "without the triage file the survivors stay untriaged" || fail "triage file not honoured: $out"
  out=$(cd "$sample" && python3 "$scripts/mutate.py" src/saturate.cpp --lines 1 2>&1 | tail -1)
  echo "$out" | grep -q "selected lines: 0 killed, 0 survived" && pass "a line range with no mutants runs nothing" || fail "empty line range: $out"
  out=$(cd "$sample" && python3 "$scripts/mutate.py" src/saturate.cpp --sample 5 --seed 7 2>&1 | head -1)
  echo "$out" | grep -q "running 5" && pass "--sample limits the run" || fail "--sample: $out"
fi

# --- capability matrix -----------------------------------------------------------------
for cxx in $compilers; do
  if "$scripts/capability_matrix.sh" "$cxx" "$sample/tests/capabilities" -std=c++20 >"$work/cap.log" 2>&1; then
    pass "capability_matrix.sh with $cxx: $(grep -c '^ok' "$work/cap.log") probes behave as declared"
  else
    fail "capability_matrix.sh with $cxx"; cat "$work/cap.log"
  fi
done
cap=$(cd "$sample" && ctest --test-dir "$(ls -d build/asan-* | head -1)" -L capability 2>&1)
echo "$cap" | grep -q "100% tests passed" && pass "ctest -L capability: 2 supported probes pass, the absent probe is a must-fail" || { fail "ctest -L capability"; echo "$cap"; }
mkdir "$work/broken"
mkdir "$work/broken/supported" "$work/broken/absent"
echo 'int main(' > "$work/broken/supported/oops.cpp"
echo 'int main() {}' > "$work/broken/absent/now_works.cpp"
"$scripts/capability_matrix.sh" "${gcc_cxx:-c++}" "$work/broken" -std=c++20 >"$work/cap.log" 2>&1 \
  && fail "capability_matrix.sh accepted a broken matrix" || { grep -q "now compiles" "$work/cap.log" && pass "an absent probe that starts compiling fails the matrix" || fail "absent-probe message"; }

echo
if [ $failures -eq 0 ]; then echo "cpp-quality-gates: all checks passed"; else echo "cpp-quality-gates: $failures check(s) failed"; fi
[ $failures -eq 0 ]
