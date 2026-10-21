#!/bin/sh
# A benchmark run in four steps: say what ran on, gate every design, prove the gate can fail, then time.
# Copy to bench/run-bench.sh together with scripts/alternate.py (as bench/alternate.py) and edit the
# variables below. A timing is only printed after every gate has passed.
#
#   OLD, NEW      the two benchmark programs; each prints CSV lines  name,detail,...,value
#   GATE_OLD,
#   GATE_NEW      correctness drivers for each design; exit 0 only when the design is correct
#   GATE_WRONG    a driver for a deliberately wrong copy; it MUST fail (empty: skip this control)
#   RUNS          repetitions of every timing (default 7)
set -eu
here=$(cd "$(dirname "$0")" && pwd)
RUNS=${RUNS:-7}
OLD=${OLD:-./build/bench_old}
NEW=${NEW:-./build/bench_new}
GATE_OLD=${GATE_OLD:-./build/gate_old}
GATE_NEW=${GATE_NEW:-./build/gate_new}
GATE_WRONG=${GATE_WRONG:-}

load() { cut -d' ' -f1 /proc/loadavg 2>/dev/null || uptime | sed 's/.*load average[s]*: *//; s/[, ].*//'; }

echo "# $(uname -m), $(nproc 2>/dev/null || sysctl -n hw.ncpu) cores, $(${CXX:-c++} --version | head -1), runs $RUNS, load $(load)"

echo "=== 1. gate: every design passes the same correctness driver"
"$GATE_OLD"
"$GATE_NEW"

if [ -n "$GATE_WRONG" ]; then
  echo "=== 2. control: the deliberately wrong copy must fail the gate"
  if "$GATE_WRONG" >/dev/null 2>&1; then echo "control FAILED: the wrong copy passed the gate"; exit 1; fi
  echo "control: the wrong copy is caught"
fi

echo "=== 3. timing, alternating the designs, median (min-max)"
python3 "$here/alternate.py" --runs "$RUNS" --balance "old=$OLD" "new=$NEW"
echo "# load at end $(load)"
