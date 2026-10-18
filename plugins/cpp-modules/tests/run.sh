#!/bin/sh
# Builds the starter template and every trap fixture and checks the recorded expectations.
# SKIP <thing> when GCC 16, a suitable CMake or Ninja is missing; a failure when WROCPP_CI=1.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
if ! command -v python3 >/dev/null 2>&1; then
  echo "SKIP python3"
  [ "${WROCPP_CI:-0}" = 1 ] && exit 1
  exit 0
fi
exec python3 -I "$here/run_tests.py"
