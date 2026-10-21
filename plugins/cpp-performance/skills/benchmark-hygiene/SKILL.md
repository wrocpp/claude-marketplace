---
name: benchmark-hygiene
description: Use before timing C++ code, when comparing two implementations or designs, when a benchmark number looks too good or too bad, or when writing a benchmark harness. Gate a baseline for correctness before it is timed, build a controlled twin, alternate the designs, report median and spread with the load average, run a scaling curve, and check the order a benchmark visits things in. Trigger phrases - "benchmark this", "compare these two", "is it faster", "microbenchmark", "median of runs", "noise", "scaling curve", "baseline", "controlled comparison", "why is the benchmark flaky".
---

# Benchmark hygiene

A timing is only worth reading when the thing timed is correct, the comparison differs in one thing, and the machine and the data did not choose the winner. Five rules, in the order to apply them.

## 1. Gate before timing

A baseline that is timed must first pass the same random-driver test as the code it is compared with, and **a deliberately wrong copy must fail that driver**. Without the second half a green gate proves only that the driver is lenient. Timing a buggy baseline is worthless: it is fast because it does less.

- The driver is seeded and compares against a plain reference (a vector summed by hand). A handful of fixed calls is not a gate: in `${CLAUDE_PLUGIN_ROOT}/tests/fixtures/gate/` the wrong copy passes `smoke` and fails the random driver at seed 1 within the first 100 steps (the exact step depends on the standard library's distributions).
- Run the gate for every design, then the wrong copy as a control; stop before any timing if either goes the wrong way. `${CLAUDE_PLUGIN_ROOT}/templates/run-bench.sh` is the skeleton: gate, control, then timing.

## 2. A controlled twin

Keep everything but the one difference identical: the same row logic, the same driver, the same data. Then the costs both sides share cancel and the difference left is the one being asked about. If a second thing differs (a different container, a different allocation pattern), the ratio answers neither question. The same holds when two trees are written separately, by two people or two agents: their row logic differs, so only the rows whose work is identical by construction (here a single insert, replace or remove) are comparable, and the rest are reported as "different code" ([honest-claims](../honest-claims/SKILL.md) rule 6).

## 3. Alternate the designs; report median, spread and load

Run the designs A B A B ... for 7 runs, not 7 of A and then 7 of B, so a drifting machine hits both. Report the median with (min-max), and the load average before and after. Do not read a difference under about 10 percent on a busy machine, or under the cost of one call, which here was 2 ns.

```sh
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/alternate.py" --runs 7 --balance old="./bench_old" new="./bench_new"
```

Each command prints CSV lines `name,detail,...,value`; the last field is the number. `--balance` reverses the order on every second run, which also cancels a "second one runs warm" effect. The load average is printed as a header; a high one means the run is a hint, not a result.

## 4. A quiet machine, then a second one

Close what you can; check the load (`uptime`). On the Mac that did the first run, differences under about 10 percent were noise; on a GitHub x86_64 runner the same benchmark had a spread under 2 percent. When a result matters, repeat it on a second machine ([measure-on-ci](../measure-on-ci/SKILL.md)).

## 5. A scaling curve, and the order things are visited in

- Run n = 100, 1,000, 10,000 and 100,000 with the same logic on both sides. A single size hides what grows: a linear row lookup read 27,827 ns per replace at 100,000 hash entries and was invisible in every single-size table.
- Check the order a benchmark visits things in. Visiting keys in insertion order is the best case for a linear scan; a shuffled second order changes the result. Say which order a number was measured in.

The recipes, including how to read a spread and what to do when two designs cross over, are in [references/checklist.md](references/checklist.md). The measured numbers and their run links are in `${CLAUDE_PLUGIN_ROOT}/skills/honest-claims/references/evidence.md`.
