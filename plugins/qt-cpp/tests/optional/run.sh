#!/bin/sh
# Build and run the reflect-moc fixtures when the toolchain is there.
# Needs: $REFLECT_MOC_DIR (a checkout of wrocpp/reflect-moc), GCC 16.2 or newer as $CXX (default g++), Qt 6.10 on
# CMAKE_PREFIX_PATH, cmake 3.30. Otherwise prints SKIP and exits 0: these fixtures are evidence for reflect-moc users, not a
# requirement of the plugin. WROCPP_CI=1 does not turn this skip into a failure; the Qt fixtures next door are required.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
cxx=${CXX:-g++}
root=${REFLECT_MOC_DIR:-}
case $root in -*) root= ;; esac

skip() {
    echo "SKIP reflect-moc fixtures ($1)"
    exit 0
}

[ -n "$root" ] && [ -f "$root/include/reflect_moc/qt/qt.hpp" ] || skip "set REFLECT_MOC_DIR to a checkout of wrocpp/reflect-moc"
command -v "$cxx" >/dev/null 2>&1 || skip "no $cxx"
command -v cmake >/dev/null 2>&1 || skip "no cmake"
version=$("$cxx" -dumpfullversion 2>/dev/null || echo 0)
case $version in 16.[2-9]* | 1[7-9].* | [2-9][0-9].*) ;; *) skip "GCC $version found, 16.2 or newer needed" ;; esac

build=$(mktemp -d)
trap 'rm -rf "$build"' EXIT
if ! cmake -S "$here" -B "$build" -DCMAKE_CXX_COMPILER="$cxx" -DREFLECT_MOC_DIR="$root" >"$build/configure.log" 2>&1; then
    if grep -q "Qt6" "$build/configure.log"; then skip "Qt 6.10 not found (set CMAKE_PREFIX_PATH)"; fi
    cat "$build/configure.log"
    echo "FAIL reflect-moc fixtures: configure failed"
    exit 1
fi
echo "== reflect-moc fixtures (GCC $version)"
cmake --build "$build" >"$build/build.log" 2>&1 || { cat "$build/build.log"; echo "FAIL reflect-moc fixtures: build failed"; exit 1; }
(cd "$build" && ctest --output-on-failure)
