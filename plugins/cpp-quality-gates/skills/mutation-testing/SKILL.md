---
name: mutation-testing
description: Use before opening a merge request that changes C++ source, when asked whether the tests would catch a bug, to find weak assertions, to triage surviving mutants, or to write the Mutation line of an MR. Trigger phrases - "mutation testing", "universalmutator", "surviving mutant", "do the tests catch this", "mutation score", "equivalent mutant", "triage", "changed lines", "test adequacy".
---

# Mutation testing

A mutant is the source with one small edit (`<` to `<=`, `+` to `-`, a deleted statement). If the tests still pass, that edit is a bug they cannot see. `scripts/mutate.py` mutates one file with universalmutator, builds and tests each mutant, and prints a verdict per mutant.

```sh
scripts/mutate.sh src/foo.cpp --build "cmake --build build/mutate" --test "ctest --test-dir build/mutate" --changed-lines origin/main
```

(`mutate.sh` creates a venv with universalmutator when `mutate` is not on PATH; `mutate.py` needs it installed. `--build` and `--test` are shell commands you type; the config never supplies shell commands. Set `mutation.build_dir`, `mutation.targets` and `mutation.tests` in `.claude/cpp-quality-gates.json` instead and the script runs `cmake --build DIR --target ...` and `ctest --test-dir DIR -R ...` itself. The build tree must already be configured and pass unmutated, or the run stops.)

## Classes

| Verdict | Meaning | Counts as |
|---|---|---|
| killed | a test failed | caught |
| killed_compile_time | build failed with the marker (`static assertion failed`) | caught |
| timeout | build or test hung | caught |
| uncompilable | build failed for another reason | no signal |
| survived | build and tests passed | a gap: kill it or triage it |

## Workflow

1. Run on the changed lines (`--changed-lines BASE_REF`) of each file you touched. `--sample N --seed S` bounds a large file; the same seed picks the same mutants, so a rerun is comparable.
2. For each `SURVIVOR UNTRIAGED <key>`, read the `-`/`+` pair and decide:
   - the edit changes behaviour: **write the test that fails on it**, rerun, count it in `--new-tests`;
   - no observable behaviour changes (`<` to `<=` where the equal case returns the same value): add `key | equivalent | reason` to the triage file;
   - the mutated code is not product behaviour (a fixture, an assertion about itself): `key | arid | reason`.
3. Finish the MR's Verification section with the last line the script prints:

```
Mutation: universalmutator, changed lines: K killed, S survived (n new tests, e equivalent, a arid)
```

or `Mutation: none, because <reason>` (docs-only change, no testable behaviour). Mutation is advice, not a merge gate: report honestly, do not hide survivors.

## Honest limits

Mutants are regex edits, not AST edits, so **many do not compile**: in the bundled sample 34 of 60 were uncompilable and give no signal. Code that mutants break at compile time (templates with concepts, `constexpr` guarded by `static_assert`) is checked by the compiler, not by the run time tests: report it as such, never as "killed by tests". A file with few runnable mutants says little; a score is a list of questions, not a grade.

Formats, flags, evidence: [references/harness.md](references/harness.md). The triage file format: `templates/mutation_triage.txt`.
