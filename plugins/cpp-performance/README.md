# cpp-performance

Measure C++ honestly, and find where a slowdown comes from. Four skills tell Claude when and how; the scripts and templates they point to run on their own, without Claude, and need only GCC and Python.

Install: `claude plugin marketplace add wrocpp/claude-marketplace && claude plugin install cpp-performance@wrocpp`

Background: [typed signals without moc](https://wrocpp.github.io/posts/qt-class-template-typed-signals-without-moc/), the Qt work these rules were learned on. Written with Claude Code; every rule is backed by a fixture that was run.

## Skills

| Skill | Prevents |
|---|---|
| `benchmark-hygiene` | timing a wrong baseline (a correctness gate with a deliberately wrong copy that must fail it), comparing designs that differ in two things (a controlled twin), reading one run (alternate, 7 runs, median and min-max, load average), a single size hiding a linear cost (scaling curve), a flattering visiting order |
| `slowdown-ladder` | blaming the wrong thing for a slowdown in one build: isolate, separate the steps, pad, read the assembly, test code placement with `-Wa,-mbranches-within-32B-boundaries` and `-falign-loops=64`, remove the fragility; perf with cpu-clock and `strace -c` when counters are missing; say what was not measured |
| `measure-on-ci` | a first figure from a busy laptop: a manual `workflow_dispatch` workflow that takes the script name as an input and runs it in the repository's image |
| `honest-claims` | a claim from one run, a ratio without the size of the cost, a benefit without the cost on the other side, a correction written beside the old claim instead of over it |

## Requirements

- GCC (16 is what the tests were run with), `objdump` (binutils), Python 3.9+.
- `tests/setup.sh` installs `lizard` (the complexity check) into a venv in `${XDG_CACHE_HOME:-~/.cache}/wrocpp/cpp-performance-venv`.
- The code-placement fixture runs on x86_64 only and prints `SKIP` elsewhere.

## Layout

```
skills/<skill>/SKILL.md          short; detail in references/
skills/honest-claims/references/evidence.md   the numbers and the CI run behind each
scripts/
  alternate.py                   run designs alternately, median (min-max), load average
  disasm_function.sh             disassemble a function by unmangled substring, <symbol> noise stripped
templates/
  bench-workflow.yml             workflow_dispatch workflow: script name as an input, runs in the repo's image
  run-bench.sh                   gate, control, then timing
tests/run.sh, tests/setup.sh     end-to-end test
tests/fixtures/gate/             a correct and a deliberately wrong Fenwick tree behind one random driver
tests/fixtures/placement_scan.cpp, tests/check_placement.py   the code-placement experiment, asserted without timing
```

## Scripts

```sh
# designs alternate A B A B; --balance reverses every second run
python3 scripts/alternate.py --runs 7 --balance old="./bench_old" new="./bench_new"

# the hot function of two builds, comparable side by side
sh scripts/disasm_function.sh ./build_a find_row > a.txt
```

`alternate.py` reads CSV lines `name,detail,...,value` from each command (last field the number; `--ignore-field K` leaves a variant-name field out of the key) and prints a Markdown table with the ratio to the first design. No shell is used: a command is split with `shlex`.

## Evidence

`sh tests/run.sh` checks, without asserting any speed:

- `alternate.py`: parsing, the alternation order (also with `--balance`), median, min and max, the ratio, and that a key missing from a run is not reported (23 tests).
- `disasm_function.sh`: finds a template function by its unmangled name, strips the `<symbol>` noise, exits 1 on no match, treats the substring as literal, refuses a binary that starts with `-`.
- The gate: the correct Fenwick tree passes the seeded random driver, the wrong copy fails it, and a fixed smoke test passes both (which is why the random driver exists). `templates/run-bench.sh` times nothing after a failed gate or a control that did not fail.
- Code placement (x86_64): with `-Wa,-mbranches-within-32B-boundaries` no fused compare-and-jump pair of the scan loop crosses or ends on a 32-byte boundary at any of 32 offsets; without it 15 of 32 offsets do.
- The workflow template: dispatchable, the script name is an input, no input reaches shell text, `actionlint` accepts it.
- Every function at cyclomatic complexity 8 or below (lizard).

| Date | Platform | Compiler | Result |
|---|---|---|---|
| 2026-10-21 | macOS arm64 | Homebrew GCC 16.2.0 | all checks pass; placement skipped (x86_64 only) |
| 2026-10-21 | Linux x86_64 (Docker `gcc:16`, emulated on an arm64 host, `WROCPP_CI=1`) | GCC 16.2.0 | all checks pass including placement |

The figures behind the rules (a 1.7 times hash-drain slowdown that was code placement, a claim that a quiet re-run reversed, a linear lookup of 27,827 ns at 100,000 entries) are in [`skills/honest-claims/references/evidence.md`](skills/honest-claims/references/evidence.md), each with its CI run link, and are valid for those runs only.

## What the evidence does not cover

- Two machines only: an Apple Silicon Mac (aarch64, in a Docker image) and GitHub's x86_64 runners (AMD EPYC). No Intel numbers, no Windows, no other compiler.
- GCC 16.2 and Qt 6.10.3. Whether a loop crosses a boundary depends on the compiler's layout and may differ with another version.
- No hardware counters: the runners are VMs where they print `<not supported>`. The mechanism of the placement effect on the AMD CPU was not identified, only that moving the loop moves the cost.
- One benchmark family (item models and signals). The figures are not claims about other code; the method is the point.
- The fixtures prove the mechanisms (a gate that can fail, a pair moved off a boundary), not that your slowdown is one of them.
