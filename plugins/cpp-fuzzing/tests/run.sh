#!/bin/sh
# Builds the fuzz-starter template and checks both directions: the correct code passes every
# compile-time check, and each planted defect fails the build at the constexpr step while the
# ordinary unit test target still builds and passes.
#   CXX=<g++ 16 or newer>   compiler to use (default: g++-16, then g++)
#   CLANGXX=<clang++>       also run the happy path with this compiler (optional)
#   WROCPP_CI=1             a missing required tool is a failure, not a SKIP
set -u
here=$(cd "$(dirname "$0")/.." && pwd)
template=$here/templates/fuzz-starter
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
failures=0

fail() { echo "FAIL $*"; failures=$((failures + 1)); }
pass() { echo "ok   $*"; }
skip() { echo "SKIP $*"; }
need() { # tool missing: a failure in CI, a skip elsewhere
  if [ "${WROCPP_CI:-0}" = 1 ]; then fail "$1 is required in CI"; else skip "$1 not installed"; fi
}

gcc_major() { "$1" -dumpversion 2>/dev/null | cut -d. -f1; }
pick_cxx() {
  for candidate in "${CXX:-}" g++-16 g++; do
    [ -n "$candidate" ] || continue
    command -v "$candidate" >/dev/null 2>&1 || continue
    case $("$candidate" --version 2>/dev/null | head -1) in *g++*|*GCC*) ;; *) continue ;; esac
    [ "$(gcc_major "$candidate")" -ge 16 ] 2>/dev/null && { echo "$candidate"; return; }
  done
}

cxx=$(pick_cxx)
if [ -z "$cxx" ] || ! command -v cmake >/dev/null 2>&1; then
  [ -z "$cxx" ] && need "g++ 16 or newer"
  command -v cmake >/dev/null 2>&1 || need cmake
  [ "$failures" -eq 0 ] && exit 0
  exit 1
fi
generator=
command -v ninja >/dev/null 2>&1 && generator="-G Ninja"
echo "compiler: $("$cxx" --version | head -1); cmake: $(cmake --version | head -1); generator: ${generator:-default}"

configure() { # dir bug [extra cmake args...]
  dir=$1 bug=$2; shift 2
  # shellcheck disable=SC2086
  cmake -S "$template" -B "$dir" $generator -DCMAKE_CXX_COMPILER="$CMAKE_CXX" -DFUZZ_STARTER_PLANTED_BUG="$bug" "$@" >"$dir.configure.log" 2>&1
}
build() { cmake --build "$1" --target "$2" >"$1.$2.log" 2>&1; }

happy_path() { # compiler label
  CMAKE_CXX=$1
  dir=$work/happy-$2
  if ! configure "$dir" none; then fail "$2: configure"; cat "$dir.configure.log"; return; fi
  if ! cmake --build "$dir" >"$dir.log" 2>&1; then fail "$2: correct code does not build"; tail -20 "$dir.log"; return; fi
  if ctest --test-dir "$dir" --output-on-failure >"$dir.ctest.log" 2>&1; then pass "$2: correct code builds and every test passes ($(grep -c 'Test *#' "$dir.ctest.log") tests)"; else fail "$2: ctest"; cat "$dir.ctest.log"; fi
}

happy_path "$cxx" gcc
if [ -n "${CLANGXX:-}" ]; then happy_path "$CLANGXX" clang; fi

CMAKE_CXX=$cxx
is_gcc=1

# variant | targets that must fail to build | text the diagnostic must contain (GCC wording)
check_variant() {
  bug=$1 expected=$2 wording=$3
  dir=$work/bug-$bug
  if ! configure "$dir" "$bug"; then fail "$bug: configure"; return; fi
  if ! build "$dir" unit_test || ! "$dir/unit_test" >/dev/null 2>&1; then fail "$bug: the ordinary unit test must build and pass"; return; fi
  broke=
  for target in constexpr_corpus_parse constexpr_corpus_summary constexpr_exhaustive_parse constexpr_exhaustive_summary; do
    if ! build "$dir" "$target"; then
      broke="$broke ${target#constexpr_}"
      if [ -n "$wording" ] && ! grep -q "$wording" "$dir.$target.log"; then fail "$bug: $target failed without '$wording'"; fi
    fi
  done
  broke=${broke# }
  if [ "$broke" = "$expected" ]; then
    pass "$bug: unit test passes, build fails at: ${broke:-nothing}"
  else
    fail "$bug: expected the constexpr failures '$expected', got '$broke'"
  fi
}

check_variant overflow "corpus_parse corpus_summary" "overflow in constant expression"
check_variant oob "corpus_parse corpus_summary exhaustive_parse exhaustive_summary" "non-constant condition for static assertion"
check_variant uninit "corpus_parse corpus_summary exhaustive_parse exhaustive_summary" "not usable in a constant expression"
check_variant null "corpus_summary exhaustive_summary" "dereferencing a null pointer"
check_variant divzero "corpus_summary exhaustive_summary" "is not a constant expression"
check_variant shift "corpus_summary" "shift expression"
check_variant roundtrip "corpus_parse exhaustive_parse" "static assertion failed: "
check_variant runtime_only "" ""

dir=$work/bug-roundtrip
grep -q "static assertion failed: a short text breaks parse_list or format_list" "$dir.constexpr_exhaustive_parse.log" \
  && pass "roundtrip: the exhaustive static_assert prints the property's message" \
  || fail "roundtrip: the exhaustive message is missing"
grep -q "static assertion failed: corpus replay: " "$dir.constexpr_corpus_parse.log" \
  && pass "roundtrip: the corpus static_assert names the corpus file" \
  || fail "roundtrip: the corpus message is missing"

# Run-time sanitizers: the defect that only exists on the run-time branch is invisible to the
# compile-time checks above and must be found by ASan on the replay binary.
probe=$work/probe.cpp
echo 'int main() {}' >"$probe"
if "$cxx" -fsanitize=address,undefined "$probe" -o "$work/probe" >/dev/null 2>&1 && "$work/probe" >/dev/null 2>&1; then
  for bug in runtime_only null overflow; do
    dir=$work/san-$bug
    configure "$dir" "$bug" -DFUZZ_STARTER_SANITIZE=ON || { fail "$bug: sanitizer configure"; continue; }
    build "$dir" fuzz_parse && build "$dir" fuzz_summary || { fail "$bug: sanitizer build"; continue; }
    caught=
    for harness in fuzz_parse fuzz_summary; do
      { "$dir/$harness" "$template/corpus" >"$dir.$harness.out" 2>&1 || caught="$caught $harness"; } 2>/dev/null
    done
    if [ -n "$caught" ]; then pass "$bug: ASan/UBSan replay catches it:$caught"; else fail "$bug: sanitizer replay found nothing"; fi
  done
else
  skip "ASan/UBSan runtime not usable with $cxx"
fi

# Crash triage helper.
findings=$work/findings
mkdir -p "$findings/default/crashes" "$findings/default/hangs"
printf '1,,' >"$findings/default/crashes/id:000000,sig:06"
printf 'x' >"$findings/default/crashes/README.txt"
printf '2,' >"$findings/default/hangs/id:000001,time:5"
if python3 -I "$template/ops/triage_crashes.py" "$findings" "$work/corpus" >"$work/triage.log" 2>&1 \
   && python3 -I "$template/ops/triage_crashes.py" "$findings" "$work/corpus" >>"$work/triage.log" 2>&1 \
   && [ "$(ls "$work/corpus" | wc -l | tr -d ' ')" = 2 ] && ls "$work/corpus" | grep -q '^crash-' && ls "$work/corpus" | grep -q '^hang-'; then
  pass "triage_crashes.py copies each finding once under a content name"
else
  fail "triage_crashes.py"; cat "$work/triage.log"
fi

# Argument hygiene: dash-leading or shell-shaped values are refused before docker is reached, and a
# crash file name is never interpreted.
canary=$work/canary
: >"$canary"
refused=1
for bad in -x 'a;touch' '../x' 'A'; do
  sh "$template/ops/fuzz.sh" "$bad" 1 >/dev/null 2>&1 && refused=0
done
sh "$template/ops/fuzz.sh" parse -5 >/dev/null 2>&1 && refused=0
sh "$template/ops/fuzz.sh" parse 1 -x >/dev/null 2>&1 && refused=0
mkdir -p "$work/hostile/default/crashes"
printf 'z' >"$work/hostile/default/crashes/"'id:000000,$(touch pwned);touch pwned2;-rf'
(cd "$work" && python3 -I "$template/ops/triage_crashes.py" "$work/hostile" "$work/hostile-corpus" >/dev/null 2>&1)
[ -n "$(ls "$work/hostile-corpus" 2>/dev/null)" ] || refused=0
if [ "$refused" = 1 ] && [ ! -e "$work/pwned" ] && [ ! -e "$work/pwned2" ] && [ -e "$canary" ]; then
  pass "fuzz.sh refuses dash-leading and shell-shaped arguments; hostile crash names are inert"
else
  fail "argument hygiene"
fi

# AFL++ is optional.
if command -v afl-fuzz >/dev/null 2>&1 && command -v afl-g++-fast >/dev/null 2>&1; then
  dir=$work/afl
  if cmake -S "$template" -B "$dir" $generator -DCMAKE_CXX_COMPILER=afl-g++-fast >"$dir.configure.log" 2>&1 \
     && cmake --build "$dir" --target fuzz_parse >"$dir.build.log" 2>&1 \
     && "$dir/fuzz_parse" "$template/corpus" >/dev/null 2>&1 \
     && AFL_SKIP_CPUFREQ=1 AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES=1 AFL_NO_UI=1 afl-fuzz -i "$template/corpus" -o "$work/afl-out" -m none -V 10 -- "$dir/fuzz_parse" >"$dir.afl.log" 2>&1 \
     && [ -d "$work/afl-out/default/queue" ]; then
    pass "AFL++ builds the harness (persistent mode), replays the corpus and runs a 10 s campaign"
  else
    fail "AFL++ build or campaign"; tail -20 "$dir.afl.log" 2>/dev/null
  fi
else
  skip "AFL++ not installed (optional)"
fi

if [ "$failures" -eq 0 ]; then echo "all checks passed"; exit 0; fi
echo "$failures check(s) failed"
exit 1
