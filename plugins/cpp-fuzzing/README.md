# cpp-fuzzing

Property-based and fuzz testing recipes for C++ where **one property function** is reused by every
kind of check: unit tests, an AFL++ harness, a compile-time replay of the corpus with `#embed`, and
a bounded-exhaustive `static_assert`. Because constant evaluation rejects undefined behaviour, a
bug the fuzzer once found, or a small input nobody tried, becomes a build error.

## Install

```
claude plugin marketplace add wrocpp/claude-marketplace && claude plugin install cpp-fuzzing@wrocpp
```

## Skills

| Skill | Use it when |
|---|---|
| `one-property-many-checks` | adding fuzz or property tests; deciding whether code can be checked for UB at compile time |
| `compile-time-corpus-and-exhaustive` | embedding a corpus with `#embed`, enumerating small inputs, tuning `-fconstexpr-ops-limit` and memory |
| `afl-harness` | writing a harness that is also a replay binary, the AFL++ Docker image, a time-boxed campaign, crash triage |

## What was measured

A planted-defect starter (`templates/fuzz-starter`, eight defects) with the unit test passing every
time. GCC 16.2 rejects signed overflow, out-of-bounds reads, null dereference, division by zero,
undefined shifts and uninitialised reads at compile time; it does not see a defect on an
`if !consteval` branch, which ASan found. Uninitialised reads were not found by ASan or UBSan at
run time. The table, diagnostics and caveats are in
`skills/one-property-many-checks/references/ub-evidence.md`.

## Requirements

- GCC 16 (C++26, `#embed`) or a recent Clang with `-std=c++2c`; CMake 3.28 or newer; Ninja
  recommended; Python 3 for `triage_crashes.py`.
- Docker, only for the AFL++ campaign (`ops/fuzz.sh`). AFL++ is optional: `tests/run.sh` reports
  `SKIP AFL++ not installed` and still exits 0.

## Layout

```
.claude-plugin/plugin.json
skills/one-property-many-checks/               SKILL.md, references/ub-evidence.md
skills/compile-time-corpus-and-exhaustive/     SKILL.md
skills/afl-harness/                            SKILL.md, references/campaign-evidence.md
templates/fuzz-starter/                        CMake project: parser, properties, harnesses, corpus,
                                               constexpr targets, planted defects, ops/ (Docker, fuzz.sh, triage)
tests/run.sh                                   builds the starter, checks both directions
tests/setup.sh                                 apt packages for a Debian gcc:16 container
```

## Tests

```bash
sh tests/run.sh                     # g++-16 on PATH, or CXX=/path/to/g++
WROCPP_CI=1 sh tests/run.sh         # a missing g++ 16 or cmake is a failure
```

The runner builds the correct starter and checks that every test passes, then for each planted
defect checks that the named constexpr targets fail with the expected diagnostic while the
ordinary unit test builds and passes. With ASan available it also checks the run-time-only defect.
`CLANGXX=clang++` adds a Clang run of the correct code.

## Licence

MIT.
