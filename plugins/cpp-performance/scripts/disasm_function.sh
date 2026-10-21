#!/bin/sh
# Print the disassembly of every function in BINARY whose unmangled name contains SUBSTRING,
# with the <symbol+offset> noise stripped from the instructions so two builds can be read side by side.
#
#   disasm_function.sh BINARY SUBSTRING
#
# Addresses stay in the output: code placement (which 32-byte block an instruction sits in) is
# what the slowdown ladder reads them for. Exit 1 when nothing matches, 2 on a bad argument.
set -eu
[ $# -eq 2 ] || { echo "usage: disasm_function.sh BINARY SUBSTRING" >&2; exit 2; }
binary=$1
needle=$2
case $binary in -*) echo "disasm_function.sh: BINARY must not start with '-'" >&2; exit 2 ;; esac
[ -f "$binary" ] || { echo "disasm_function.sh: no such file: $binary" >&2; exit 2; }
[ -n "$needle" ] || { echo "disasm_function.sh: SUBSTRING is empty" >&2; exit 2; }

# The needle travels in the environment and is matched with index(), so it is a plain substring
# and cannot be read as an awk option, an escape or a pattern. A function ends at its blank line.
export NEEDLE=$needle
matches=$(objdump -d -C --no-show-raw-insn "$binary" | awk '
  BEGIN { needle = ENVIRON["NEEDLE"] }
  /^[0-9a-f]+ <.*>:$/ { printing = index($0, needle) > 0; if (printing) { found = 1; if (count++) print ""; print }; next }
  !NF { printing = 0; next }
  printing { gsub(/ *<.*>$/, ""); print }
  END { exit found ? 0 : 1 }
') || { echo "disasm_function.sh: no function matching '$needle' in $binary" >&2; exit 1; }
printf '%s\n' "$matches"
