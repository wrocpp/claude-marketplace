#!/bin/sh
# Contract for CI: exit 0 when every test and fixture passes.
# WROCPP_CI=1   a compiler that is not installed is a failure (otherwise `SKIP <compiler>`)
# WROCPP_NETWORK=1  also fetch mp-units and run the optional fixtures against it
set -eu
here=$(cd "$(dirname "$0")" && pwd)
export PYTHONDONTWRITEBYTECODE=1
echo "== scanner, cppreference helper and hook probes"
python3 "$here/test_scripts.py"
echo "== untrusted input (hook output and helper arguments)"
python3 "$here/test_untrusted.py"
echo "== compiler fixtures"
python3 "$here/check_fixtures.py"
echo "== optional mp-units fixtures"
sh "$here/optional/run.sh"
