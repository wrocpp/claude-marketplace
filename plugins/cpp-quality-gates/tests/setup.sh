#!/bin/sh
# Install what tests/run.sh needs: build tools through apt when run as root on Debian or Ubuntu,
# and lizard, gcovr and universalmutator into a venv (QG_VENV, default under ~/.cache) with pip.
set -eu
if [ "$(id -u)" -eq 0 ] && command -v apt-get >/dev/null 2>&1; then
  apt-get update -qq
  apt-get install -y -qq --no-install-recommends cmake ninja-build python3 python3-venv git ca-certificates >/dev/null
fi
venv=${QG_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/wrocpp/cpp-quality-gates-venv}
[ -x "$venv/bin/pip" ] || python3 -m venv "$venv"
"$venv/bin/pip" install -q lizard gcovr universalmutator
echo "setup: tools in $venv"
