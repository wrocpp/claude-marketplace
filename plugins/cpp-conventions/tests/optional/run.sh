#!/bin/sh
# Compile the mp-units fixtures when mp-units is available.
# Looks for $MP_UNITS_DIR (a checkout of mpusz/mp-units, v2.x layout), then, when WROCPP_NETWORK=1,
# clones the pinned tag into the cache. Otherwise prints SKIP and exits 0.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
tag=v2.5.0
root=${MP_UNITS_DIR:-}
if [ -z "$root" ] && [ "${WROCPP_NETWORK:-0}" = 1 ]; then
    cache=${WROCPP_CACHE_DIR:-${XDG_CACHE_HOME:-$HOME/.cache}/wrocpp}/mp-units-$tag
    if [ ! -d "$cache/src/core/include" ]; then
        rm -rf "$cache"
        mkdir -p "$(dirname "$cache")"
        git clone --quiet --depth 1 --branch "$tag" https://github.com/mpusz/mp-units "$cache" || { echo "FAIL mp-units: clone of $tag failed"; exit 1; }
    fi
    root=$cache
fi
if [ -z "$root" ] || [ ! -d "$root/src/core/include" ]; then
    echo "SKIP mp-units fixtures (set MP_UNITS_DIR to a v2.x checkout, or WROCPP_NETWORK=1 to clone $tag)"
    exit 0
fi
exec python3 "$here/../check_fixtures.py" --dir "$here" --include "$root/src/core/include" --include "$root/src/systems/include"
