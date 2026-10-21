#!/usr/bin/env python3
"""The code-placement experiment, asserted without timing anything.

    check_placement.py COMPILER

Compiles fixtures/placement_scan.cpp to assembly once, removes the compiler's own .p2align lines, and
moves the function by PAD = 0 .. 31 bytes (a gas symbol) in two builds: plain, and with
-Wa,-mbranches-within-32B-boundaries. In the disassembly of scan_for_key it looks at every fused
compare-and-jump pair and asks whether it crosses a 32-byte boundary or ends on one.

Asserted: the flag is accepted; the loop is present (at least one pair); with the flag no pair crosses
or ends on a boundary at any PAD; without it at least one PAD puts a pair there, so the experiment can
show something. The only thing run is one build of each, to see that the program prints its line.
Prints SKIP and exits 0 on a machine that is not x86_64.
"""
import os
import pathlib
import platform
import re
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
FIXTURE = HERE / "fixtures" / "placement_scan.cpp"
DISASM = HERE.parent / "scripts" / "disasm_function.sh"
FUNCTION = "scan_for_key"
BLOCK = 32
PADS = range(BLOCK)
X86_MACHINES = ("x86_64", "AMD64")
COMPILE = ["-std=c++20", "-O2", "-fno-tree-vectorize", "-fno-unroll-loops", "-fno-toplevel-reorder"]
PLACEMENT_FLAG = "-Wa,-mbranches-within-32B-boundaries"
INSTRUCTION = re.compile(r"^\s*([0-9a-f]+):\s+(\S+)")
COMPARES = ("cmp", "test")


def run(argv, **kwargs):
    return subprocess.run(argv, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, **kwargs)


def instructions(listing):
    """[(address, mnemonic)] from the output of disasm_function.sh."""
    found = []
    for line in listing.splitlines():
        match = INSTRUCTION.match(line)
        if match:
            found.append((int(match.group(1), 16), match.group(2)))
    return found


def is_conditional_jump(mnemonic):
    return mnemonic.startswith("j") and mnemonic != "jmp"


def fused_pairs(listing):
    """[(start, end)] of each compare followed directly by a conditional jump."""
    items = instructions(listing)
    pairs = []
    for (start, mnemonic), (middle, jump), following in zip(items, items[1:], items[2:] + [(None, None)]):
        if mnemonic in COMPARES and is_conditional_jump(jump) and following[0] is not None:
            pairs.append((start, following[0]))
    return pairs


def on_boundary(pair):
    start, end = pair
    return start // BLOCK != (end - 1) // BLOCK or end % BLOCK == 0


def build(compiler, assembly, pad, flags, out):
    run([compiler, str(assembly), f"-Wa,--defsym,PAD={pad}", *flags, "-o", str(out)])
    return run(["sh", str(DISASM), str(out), FUNCTION]).stdout


def assembly_without_alignment(compiler, work):
    raw = work / "raw.s"
    run([compiler, *COMPILE, "-S", str(FIXTURE), "-o", str(raw)])
    stripped = work / "scan.s"
    kept = [line for line in raw.read_text().splitlines(keepends=True) if not line.lstrip().startswith(".p2align")]
    stripped.write_text("".join(kept))
    return stripped


def pairs_at_every_pad(compiler, assembly, flags, out):
    return {pad: fused_pairs(build(compiler, assembly, pad, flags, out)) for pad in PADS}


def program_failures(work):
    failures = []
    for variant in ("plain", "padded"):
        line = run([str(work / variant), variant]).stdout.strip()
        if not line.startswith(f"placement,{variant},"):
            failures.append(f"the {variant} build printed {line!r}")
    return failures


def experiment(compiler):
    with tempfile.TemporaryDirectory() as directory:
        work = pathlib.Path(directory)
        assembly = assembly_without_alignment(compiler, work)
        plain = pairs_at_every_pad(compiler, assembly, [], work / "plain")
        padded = pairs_at_every_pad(compiler, assembly, [PLACEMENT_FLAG], work / "padded")
        return judge(plain, padded) + program_failures(work)


def main(argv):
    if len(argv) != 2:
        print(__doc__.strip().splitlines()[2], file=sys.stderr)
        return 2
    if platform.machine() not in X86_MACHINES:
        print(f"SKIP placement: {platform.machine()} is not x86_64")
        return 0
    failures = experiment(argv[1])
    for failure in failures:
        print(f"FAIL placement: {failure}")
    if not failures:
        print(f"PASS placement: the loop is present, {PLACEMENT_FLAG} is accepted, and with it no fused pair crosses or ends on a {BLOCK}-byte boundary at any of {len(PADS)} offsets")
    return 1 if failures else 0


def offsets_on_boundary(by_pad):
    return [pad for pad, pairs in by_pad.items() if any(on_boundary(p) for p in pairs)]


def judge(plain, padded):
    failures = []
    if not all(plain.values()) or not all(padded.values()):
        failures.append(f"no compare-and-jump pair found in {FUNCTION}: the loop is not in the disassembly")
    if offsets_on_boundary(padded):
        failures.append(f"with the flag a pair still sits on a boundary at pad {offsets_on_boundary(padded)}")
    bad_plain = offsets_on_boundary(plain)
    if not bad_plain:
        failures.append("without the flag no offset put a pair on a boundary: the experiment shows nothing")
    else:
        print(f"note placement: without the flag {len(bad_plain)} of {len(PADS)} offsets put a pair on a boundary")
    return failures


if __name__ == "__main__":
    sys.exit(main(sys.argv))
