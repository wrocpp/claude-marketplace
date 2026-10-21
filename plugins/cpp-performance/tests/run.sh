#!/bin/sh
# End-to-end test of cpp-performance. Exit 0 when every check passes. Nothing here asserts a speed.
# A missing tool is "SKIP"; with WROCPP_CI=1 a skip fails, except the x86_64-only placement check on another CPU.
# Env: CXX (compiler; default g++-16, g++, c++ in that order)
set -u
here=$(cd "$(dirname "$0")" && pwd)
plugin=$(dirname "$here")
venv=${PERF_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/wrocpp/cpp-performance-venv}
[ -d "$venv/bin" ] && PATH="$venv/bin:$PATH"
export PATH

failures=0
pass() { echo "PASS $*"; }
fail() { echo "FAIL $*"; failures=$((failures + 1)); }
skip() { echo "SKIP $*"; [ "${WROCPP_CI:-0}" = 1 ] && failures=$((failures + 1)); }
max_complexity=8

cxx=
for candidate in "${CXX:-}" g++-16 g++ c++; do
  [ -n "$candidate" ] && command -v "$candidate" >/dev/null 2>&1 && { cxx=$candidate; break; }
done
[ -n "$cxx" ] || { echo "FAIL no C++ compiler found"; exit 1; }
command -v python3 >/dev/null 2>&1 && command -v objdump >/dev/null 2>&1 || { echo "FAIL python3 and objdump are required"; exit 1; }
work=$(cd "$(mktemp -d)" && pwd -P)
trap 'rm -rf "$work"' EXIT INT TERM
echo "compiler: $cxx ($($cxx -dumpfullversion 2>/dev/null || echo unknown)), machine $(uname -m)"

# --- alternate.py ------------------------------------------------------------------------
if out=$(python3 "$here/test_alternate.py" 2>&1); then pass "alternate.py: $(echo "$out" | grep -E '^Ran ')"; else fail "alternate.py unit tests"; echo "$out" | tail -20; fi

# --- disasm_function.sh ------------------------------------------------------------------
disasm=$plugin/scripts/disasm_function.sh
if $cxx -std=c++20 -O1 "$here/fixtures/disasm_target.cpp" -o "$work/target" 2>"$work/cc.log"; then
  out=$("$disasm" "$work/target" "perf_fixture::sum_to<int>" 2>&1); code=$?
  if [ $code -eq 0 ] && echo "$out" | grep -q "^[0-9a-f]* <.*perf_fixture::sum_to<int>(int)>:$"; then pass "disasm_function.sh finds a template function by its unmangled name"; else fail "disasm_function.sh by unmangled name (rc=$code): $out"; fi
  body=$(echo "$out" | sed 1d)
  if [ -n "$body" ] && ! echo "$body" | grep -q '[<>]'; then pass "disasm_function.sh strips the <symbol> noise from the instructions"; else fail "disasm_function.sh left <...> in the instructions"; fi
  out=$("$disasm" "$work/target" main 2>&1)
  if echo "$out" | grep -q "sum_to" ; then fail "main's call target kept its symbol"; else pass "disasm_function.sh strips the symbol from a call (main calls sum_to)"; fi
  "$disasm" "$work/target" "no_such_function" >/dev/null 2>&1; [ $? -eq 1 ] && pass "disasm_function.sh exits 1 when nothing matches" || fail "disasm_function.sh no-match exit code"
  "$disasm" "$work/target" "sum.*" >/dev/null 2>&1; [ $? -eq 1 ] && pass "the substring is literal, not a pattern" || fail "disasm_function.sh read the substring as a pattern"
  "$disasm" "-delete" main >/dev/null 2>&1; [ $? -eq 2 ] && pass "disasm_function.sh refuses a binary that starts with '-'" || fail "disasm_function.sh leading dash"
  "$disasm" "$work/target" >/dev/null 2>&1; [ $? -eq 2 ] && pass "disasm_function.sh refuses a missing argument" || fail "disasm_function.sh argument count"
else
  fail "disasm target does not compile: $(tail -3 "$work/cc.log")"
fi

# --- gate before timing ------------------------------------------------------------------
gate_dir=$here/fixtures/gate
for impl in correct wrong; do
  $cxx -std=c++20 -Wall -Wextra -Werror -I"$gate_dir" -DIMPL_HEADER="\"fenwick_$impl.hpp\"" "$gate_dir/gate_driver.cpp" -o "$work/gate_$impl" 2>"$work/cc.log" || { fail "gate driver with the $impl copy does not compile: $(tail -3 "$work/cc.log")"; continue; }
done
if [ -x "$work/gate_correct" ] && [ -x "$work/gate_wrong" ]; then
  out=$("$work/gate_correct"); code=$?
  [ $code -eq 0 ] && echo "$out" | grep -q '^gate,PASS' && pass "the gate passes the correct implementation" || fail "the gate rejected the correct implementation: $out"
  out=$("$work/gate_wrong"); code=$?
  [ $code -eq 1 ] && echo "$out" | grep -q '^gate,FAIL' && pass "the gate fails the deliberately wrong copy: $out" || fail "the gate passed the wrong copy (rc=$code): $out"
  "$work/gate_wrong" smoke >/dev/null && "$work/gate_correct" smoke >/dev/null && pass "a fixed smoke test passes the wrong copy too, so the random driver is what catches it" || fail "the smoke test no longer shows why a random driver is needed"
fi

# --- code placement ----------------------------------------------------------------------
out=$(python3 "$here/check_placement.py" "$cxx" 2>&1); code=$?
echo "$out"
if echo "$out" | grep -q '^SKIP placement'; then
  [ "$(uname -m)" = x86_64 ] && fail "placement was skipped on x86_64" || echo "NOTE placement: x86_64 only, not run on $(uname -m); CI runs it"
elif [ $code -eq 0 ]; then pass "check_placement.py"; else fail "check_placement.py (rc=$code)"; fi

# --- run-bench.sh template, end to end ---------------------------------------------------
template=$plugin/templates/run-bench.sh
mkdir "$work/bench" && cp "$template" "$plugin/scripts/alternate.py" "$work/bench/" && cp "$here/fixtures/bench_pair.sh" "$work/bench/"
run_template() { (cd "$work" && env "$@" sh bench/run-bench.sh 2>&1); }
out=$(run_template RUNS=3 OLD="sh bench/bench_pair.sh 10" NEW="sh bench/bench_pair.sh 20" GATE_OLD="$work/gate_correct" GATE_NEW="$work/gate_correct" GATE_WRONG="$work/gate_wrong"); code=$?
if [ $code -eq 0 ] && echo "$out" | grep -q "control: the wrong copy is caught" && echo "$out" | grep -q "| fill,100 | 10.0 (10.0-10.0) | 20.0 (20.0-20.0) | 2.00 |"; then pass "run-bench.sh gates, proves the gate can fail, then times"; else fail "run-bench.sh (rc=$code): $out"; fi
out=$(run_template RUNS=3 OLD="sh bench/bench_pair.sh 10" NEW="sh bench/bench_pair.sh 20" GATE_OLD="$work/gate_correct" GATE_NEW="$work/gate_wrong"); code=$?
if [ $code -ne 0 ] && ! echo "$out" | grep -q "=== 3"; then pass "run-bench.sh times nothing when a design fails the gate"; else fail "run-bench.sh timed a design that failed the gate (rc=$code)"; fi
out=$(run_template RUNS=3 OLD="sh bench/bench_pair.sh 10" NEW="sh bench/bench_pair.sh 20" GATE_OLD="$work/gate_correct" GATE_NEW="$work/gate_correct" GATE_WRONG="$work/gate_correct"); code=$?
if [ $code -ne 0 ] && echo "$out" | grep -q "control FAILED" && ! echo "$out" | grep -q "=== 3"; then pass "run-bench.sh stops when the control does not fail"; else fail "run-bench.sh accepted a control that passed (rc=$code)"; fi

# --- workflow template -------------------------------------------------------------------
wf=$plugin/templates/bench-workflow.yml
grep -q "workflow_dispatch:" "$wf" && grep -q "script:" "$wf" && grep -q 'bench/\*\.sh' "$wf" && pass "bench-workflow.yml is dispatchable and takes the script name as an input" || fail "bench-workflow.yml shape"
grep -n '\${{ *inputs\.' "$wf" | grep -v -E "^[0-9]+:\s+(SCRIPT|RUNS): " >"$work/inline.txt"
[ -s "$work/inline.txt" ] && fail "an input is used outside an env: block: $(head -2 "$work/inline.txt")" || pass "bench-workflow.yml passes inputs through env, never into the shell text"
if command -v actionlint >/dev/null 2>&1; then
  out=$(actionlint "$wf" 2>&1) && pass "actionlint accepts bench-workflow.yml" || fail "actionlint: $out"
else
  echo "NOTE actionlint not installed here; the CI workflows job lints the template"
fi

# --- complexity and magic numbers --------------------------------------------------------
if command -v lizard >/dev/null 2>&1; then
  out=$(lizard -C "$max_complexity" -w "$plugin/scripts" "$here/check_placement.py" "$here/fixtures/gate" "$here/fixtures/placement_scan.cpp" 2>&1) && pass "every function has cyclomatic complexity <= $max_complexity" || fail "complexity above $max_complexity: $out"
else
  skip "complexity: lizard not installed (run tests/setup.sh)"
fi

echo
if [ $failures -eq 0 ]; then echo "cpp-performance: all checks passed"; else echo "cpp-performance: $failures check(s) failed"; fi
[ $failures -eq 0 ]
