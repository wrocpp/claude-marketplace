#!/bin/sh
# Runs the unit tests, the lint self-tests, the hook payload tests and the GCC probes.
# Exit 0 when everything passes. With WROCPP_CI=1 a missing GCC 16 is a failure, not a skip.
set -u
here=$(cd "$(dirname "$0")" && pwd)
plugin=$(dirname "$here")
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT INT TERM
PYTHONDONTWRITEBYTECODE=1
export PYTHONDONTWRITEBYTECODE
failures=0
ran=0

fail() {
    echo "FAIL $1"
    failures=$((failures + 1))
}

section() {
    echo "== $1"
}

section "python unit tests"
if python3 -m unittest discover -s "$here" -p 'test_*.py' >"$work/unit" 2>&1; then
    tail -n 3 "$work/unit"
else
    cat "$work/unit"
    fail "python unit tests"
fi

section "hostile config and source text never reach hook output"
python3 "$here/test_injection.py" >"$work/injection" 2>&1 || {
    cat "$work/injection"
    fail "injection tests"
}

section "malformed or wrong-typed config keeps the guard on"
python3 "$here/test_config.py" >"$work/config" 2>&1 || {
    cat "$work/config"
    fail "config tests"
}

section "lint self-tests"
for lint in reflection_lint cpp26_lint; do
    python3 "$plugin/scripts/$lint.py" --self-test || fail "$lint self-test"
done

gcc16() {
    for candidate in g++-16 g++; do
        command -v "$candidate" >/dev/null 2>&1 || continue
        case $("$candidate" --version 2>&1) in *clang*) continue ;; esac
        major=$("$candidate" -dumpversion 2>/dev/null | cut -d. -f1)
        if [ "${major:-0}" -ge 16 ] 2>/dev/null; then
            echo "$candidate"
            return 0
        fi
    done
    return 1
}

flags="-std=c++26 -freflection -fsyntax-only"

section "GCC 16 probes"
if cxx=$(gcc16); then
    echo "compiler: $("$cxx" --version | head -n 1)"
    for probe in "$here"/probes/supported/*.cpp; do
        [ -e "$probe" ] || continue
        ran=$((ran + 1))
        # shellcheck disable=SC2086
        if "$cxx" $flags "$probe" >"$work/out" 2>&1; then
            echo "ok   supported/$(basename "$probe")"
        else
            fail "supported/$(basename "$probe") must compile"
            head -n 5 "$work/out"
        fi
    done
    for probe in "$here"/probes/absent/*.cpp; do
        [ -e "$probe" ] || continue
        ran=$((ran + 1))
        # shellcheck disable=SC2086
        if "$cxx" $flags "$probe" >"$work/out" 2>&1; then
            fail "absent/$(basename "$probe") compiled, so the finding is out of date"
        elif grep -q "internal compiler error" "$work/out"; then
            fail "absent/$(basename "$probe") crashed the compiler instead of rejecting"
        else
            echo "ok   absent/$(basename "$probe") is rejected"
        fi
    done
    section "reference implementation"
    ran=$((ran + 1))
    if "$cxx" -std=c++26 -freflection -Wall -Wextra -Werror "$here/reference_selftest.cpp" -o "$work/reference" >"$work/out" 2>&1 && "$work/reference"; then
        echo "ok   reference_selftest.cpp builds warning-free and runs"
    else
        fail "reference_selftest.cpp"
        head -n 20 "$work/out"
    fi
else
    echo "SKIP g++-16"
    if [ "${WROCPP_CI:-0}" = 1 ]; then
        fail "g++-16 is required when WROCPP_CI=1"
    fi
fi

echo "== $ran compiler checks, $failures failed"
[ "$failures" -eq 0 ]
