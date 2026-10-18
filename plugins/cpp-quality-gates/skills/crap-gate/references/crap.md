# CRAP in detail

## Definition

Change Risk Anti-Patterns: `CRAP = CC^2 * (1 - cov)^3 + CC`.

- `CC` counts independent paths: 1, plus one for each `if`, `for`, `while`, `case`, `catch`, `&&`, `||` and `?:` that lizard sees.
- `cov` is the covered fraction of the function's instrumented lines (gcov line coverage, from gcovr).
- The cube makes the first tests cheap and the last ones cheap too: going from 0% to 50% removes 87% of the penalty term.
- At `cov = 1` the term vanishes and CRAP = CC. At `cov = 0` it is CC^2 + CC.

Why 8: a function of CC 8 is the largest you can fully cover and still pass; it forces a split exactly where a reader starts to lose the thread. The limit is a parameter (`--max`, `crap.max`).

## What the pipeline does

1. `cmake --preset coverage` builds with `--coverage -O0` (template preset); `ctest` runs the tests.
2. `gcovr --json` writes per-line counts. A line counts as covered when any instance ran it, so a template instantiated twice is covered if either ran.
3. `crap.py` runs lizard over each source file under the roots, finds each function's line range, takes the covered fraction of the lines in that range and applies the formula.

## Edge cases the script decides

| Case | Behaviour | Why |
|---|---|---|
| File not in the coverage report | coverage 0 (`--missing covered` to change) | no test compiled it |
| Function with no instrumented line (pure `constexpr`, evaluated at compile time) | coverage 1 | nothing could run |
| Header function | scored if the header is under a root and the report lists it | filter the report with `coverage.filters` |

## Limits

- Line coverage is not branch coverage: `classify` above shows 92% from one call because every `else if` line is evaluated. Treat a high-CC function with high line coverage as untested until each branch has an assertion (the mutation harness checks exactly that).
- gcc and clang use different coverage formats. With Apple clang use a GCC (`gcov-N` beside `g++-N`) for this pipeline, or `llvm-cov gcov`.
- gcov records real paths. When the project directory is reached through a symlink (macOS `/var` is `/private/var`), `gcovr -r` must be the physical path; `coverage.sh` passes `pwd -P`.
- lizard parses C++ approximately; macros and exotic templates can misattribute a line range. Check a surprising score by reading the function.
