# Mutation harness reference

## Command line

`mutate.py SOURCE [--build CMD] [--test CMD] [--changed-lines BASE_REF | --lines 10-20,31] [--sample N] [--seed S] [--triage FILE] [--ignore FILE] [--new-tests N] [--compile-time-marker TEXT] [--build-timeout S] [--test-timeout S] [--config FILE]`

- Run from the project root. `--build` and `--test` are shell commands; the source file is overwritten per mutant and restored afterwards, also on Ctrl-C or SIGTERM. Do not edit the file while it runs.
- `--sample 0` runs every mutant (default 200). The sample is drawn with `random.Random(seed)` over the generated list.
- `--changed-lines` runs `git diff -U0 BASE_REF -- SOURCE` and mutates only added or changed lines.
- Exit 0 after reporting; 1 only for the harness failing (unmutated tree does not build or pass, universalmutator missing, bad triage kind).

## Triage file

One line per survivor: `key | kind | reason`. Key is `<file>:<line>:<first 8 hex of sha1 of the mutated line>`, printed on the `SURVIVOR` line. Kind is `equivalent` or `arid`. `#` starts a comment. Because the key includes the mutated text, editing the line or a universalmutator update that changes its rules makes old keys stale: survivors reappear as `UNTRIAGED`, which is the intended prompt to look again.

## Ignore file

Regexes of source lines universalmutator must not mutate (`templates/mutation_ignore.txt`: `static_assert`, includes, module declarations).

## Evidence

Bundled sample `src/saturate.cpp` (a saturating add, 8 tests), full run, `tests/run.sh`:

| Date | Compiler | universalmutator | Mutants | Killed | Survived | Uncompilable |
|---|---|---|---|---|---|---|
| 2026-10-18 | g++ 16.2.0 (Homebrew), macOS arm64 | 1.14.1 | 60 | 23 | 3 (all equivalent: swapped commutative parameters, `<` to `<=` and `>` to `>=` at the bound) | 34 |

Cost: about 10 s for 60 mutants of a three-line function with Ninja, so the cost is the build, not the mutation. Keep the mutation build target small (one test target), as the sample does.
