---
name: slowdown-ladder
description: Use when a C++ function is slower in one build than in another build that runs the same loop, when a benchmark gap does not match the code, or when a profile or counter is not available. Climb in order - reproduce in isolation, separate the steps with no framework, shift the data layout with padding, read the assembly of the hot function in both builds, test code placement with -Wa,-mbranches-within-32B-boundaries and -falign-loops=64, then remove the fragility - and say plainly what could not be measured. Trigger phrases - "slower in one build", "same code different speed", "why is this 1.7 times slower", "perf record", "objdump", "code alignment", "jcc erratum", "32-byte boundary", "hardware counters not supported", "strace -c".
---

# Slowdown ladder

A slowdown that shows in one build and not in the other, with the same source in the loop, is a measurement problem or a code-placement problem before it is a design problem. Climb in order and stop at the rung that answers it. Do not blame the thing you changed until the rungs below say so.

1. **Reproduce in isolation.** One binary, one container, alternating runs ([benchmark-hygiene](../benchmark-hygiene/SKILL.md)). If it vanishes (it did on aarch64 where it had shown on x86_64), the cause is the machine or the load, not the code.
2. **Separate the steps, with no framework.** Write a probe that does only the suspect steps (scan, remove, both) with no signals, no model, no fixture. If the probe shows the gap, the framework is cleared.
3. **Shift the data layout.** Allocate pad bytes first (0, 4, 8 ... 4096) and repeat. If the figure does not follow the padding, the data layout is cleared.
4. **Read the assembly of the hot function in both builds.** Compile with `-S`, or dump the binary:

   ```sh
   sh "${CLAUDE_PLUGIN_ROOT}/scripts/disasm_function.sh" ./build_a find_row > a.txt
   sh "${CLAUDE_PLUGIN_ROOT}/scripts/disasm_function.sh" ./build_b find_row > b.txt
   ```

   The script is `objdump -d -C` for the unmangled name, with the `<...>` noise stripped (`sed 's/<[^>]*>//g'` by hand). Same instructions in both? Then the difference is where they sit: look at the addresses of the compare and the jump that close the loop, and whether the pair crosses a 32-byte boundary (an address whose low five bits wrap).
5. **Test the hypothesis, in both builds.** `-Wa,-mbranches-within-32B-boundaries` keeps fused compare-and-jump pairs off boundaries; `-falign-loops=64` moves the loop head. If the first makes the builds equal and the second makes them both slow, moving the loop moves the cost. The fixture in `${CLAUDE_PLUGIN_ROOT}/tests/fixtures/placement_scan.cpp` and `${CLAUDE_PLUGIN_ROOT}/tests/check_placement.py` show the mechanism without timing: without the flag 15 of 32 one-byte offsets put a pair on a boundary, with it none does (GCC 16.2, x86_64).
6. **Remove the fragility, do not tune it.** A flag that fixes one build is a bet on the next compiler. Change the code so the cost does not depend on placement: here a `std::vector` and `std::find` for the key list gave 7.6 microseconds a removal in both builds.

## When the tools are missing

- `perf record -e cpu-clock` samples by timer when hardware counters print `<not supported>` (a VM). It shows where the time goes, not why: cycles, instructions and branch misses were not read.
- `strace -c` separates system time from user time: system time under 0.01 s and start-up calls only means the cost is user code.
- **Say what could not be measured and that the mechanism was not identified.** On an AMD EPYC this was not the Intel jcc erratum by name; the finding was only that moving the loop moves the cost.

Commands, the probe layout and the numbers of each rung are in [references/ladder.md](references/ladder.md); the CI runs behind them are in `${CLAUDE_PLUGIN_ROOT}/skills/honest-claims/references/evidence.md`.
