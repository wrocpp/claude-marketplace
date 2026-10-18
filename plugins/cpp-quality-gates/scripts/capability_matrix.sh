#!/bin/sh
# Run a capability matrix without CMake.
# usage: capability_matrix.sh COMPILER DIR [FLAGS...]
# DIR/supported/*.cpp must compile, DIR/absent/*.cpp must not. Prints one line per probe,
# exits 1 when any behaves differently. Probes are compiled with -fsyntax-only.
set -eu
[ $# -ge 2 ] || { echo "usage: capability_matrix.sh COMPILER DIR [FLAGS...]" >&2; exit 2; }
cxx=$1 dir=$2
shift 2
failed=0
for probe in "$dir"/supported/*.cpp; do
  [ -e "$probe" ] || continue
  if "$cxx" "$@" -fsyntax-only "$probe" >/dev/null 2>&1; then echo "ok      supported $(basename "$probe")"
  else echo "FAIL    supported $(basename "$probe") does not compile"; failed=1; fi
done
for probe in "$dir"/absent/*.cpp; do
  [ -e "$probe" ] || continue
  if "$cxx" "$@" -fsyntax-only "$probe" >/dev/null 2>&1; then echo "FAIL    absent    $(basename "$probe") now compiles: remove the workaround"; failed=1
  else echo "ok      absent    $(basename "$probe")"; fi
done
exit $failed
