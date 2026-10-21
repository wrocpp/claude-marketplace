#!/bin/sh
# Contract for CI: exit 0 when every test and fixture passes.
# WROCPP_CI=1        a missing Qt 6, cmake or compiler is a failure (otherwise `SKIP <what>` and exit 0)
# REFLECT_MOC_DIR    a checkout of wrocpp/reflect-moc: also run the optional fixtures that need it (GCC 16.2, Qt 6.10)
# CMAKE_PREFIX_PATH  where Qt 6 is, when it is not on the system path
set -eu
here=$(cd "$(dirname "$0")" && pwd)
export PYTHONDONTWRITEBYTECODE=1
ulimit -c 0 2>/dev/null || true  # the thread and name checks abort a child on purpose; leave no core files


missing() {
    if [ "${WROCPP_CI:-0}" = 1 ]; then
        echo "FAIL $1 (WROCPP_CI=1)"
        exit 1
    fi
    echo "SKIP $1"
}

echo "== Qt fixtures"
build=$(mktemp -d)
trap 'rm -rf "$build"' EXIT
if ! command -v cmake >/dev/null 2>&1; then
    missing "Qt fixtures: cmake is not installed"
elif ! cmake -S "$here" -B "$build" >"$build/configure.log" 2>&1; then
    if grep -q "Qt6" "$build/configure.log"; then
        missing "Qt fixtures: Qt 6 (Core, Test) not found; install qt6-base-dev or set CMAKE_PREFIX_PATH"
    else
        cat "$build/configure.log"
        echo "FAIL Qt fixtures: configure failed"
        exit 1
    fi
else
    skipped=$(sed -n 's/^-- QT_CPP_SKIP //p' "$build/configure.log")
    [ -z "$skipped" ] || missing "Qt fixtures: $skipped"
    cmake --build "$build" >"$build/build.log" 2>&1 || { cat "$build/build.log"; echo "FAIL Qt fixtures: build failed"; exit 1; }
    (cd "$build" && ctest --output-on-failure)
    echo "== what the control runs reported"
    "$build/contract_flaws_detected" 2>/dev/null
fi

