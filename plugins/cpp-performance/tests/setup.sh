#!/bin/sh
# Install what tests/run.sh needs: python3 through apt when run as root on Debian or Ubuntu, and lizard
# (the cyclomatic-complexity check) into a venv (PERF_VENV, default under ~/.cache) with pip.
# The compiler is not installed here: use GCC 16 (the gcc:16 image has it).
set -eu
if [ "$(id -u)" -eq 0 ] && command -v apt-get >/dev/null 2>&1; then
  apt-get update -qq
  apt-get install -y -qq --no-install-recommends python3 python3-venv binutils >/dev/null
fi
venv=${PERF_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/wrocpp/cpp-performance-venv}
[ -x "$venv/bin/pip" ] || python3 -m venv "$venv"
"$venv/bin/pip" install -q lizard
echo "setup: lizard in $venv"
