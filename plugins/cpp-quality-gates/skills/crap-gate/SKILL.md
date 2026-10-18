---
name: crap-gate
description: Use when a C++ change must meet a complexity-and-coverage bar, when asked to measure or lower CRAP, to set up a CRAP gate in CI, to explain why a function fails with 100% coverage, or before opening a merge request that adds or touches functions. Trigger phrases - "CRAP score", "CRAP gate", "cyclomatic complexity", "coverage gate", "lizard", "gcovr", "split this function", "function too complex", "is it tested enough".
---

# CRAP gate

CRAP(f) = CC^2 * (1 - cov)^3 + CC, where CC is the cyclomatic complexity of function `f` and `cov` the fraction of its lines that ran in the tests. The default limit is 8: every function you add or touch stays at or under it.

At full coverage the score is CC, so **a function with CC >= 9 fails however well it is tested**; the only fix is to split it. Below that, the table says how much coverage a function needs:

| CC | 3 | 4 | 5 | 6 | 7 | 8 | 9+ |
|---|---|---|---|---|---|---|---|
| line coverage needed to pass 8 | 18% | 37% | 51% | 62% | 73% | 100% | never |

Worked example, from the bundled sample (`tests/sample`, GCC 16.2): `weekday` is a switch with eight cases, CC 9, 100% covered, CRAP 9.0 and fails. `classify` is CC 15 and 92% covered: 15^2 * 0.08^3 + 15 = 15.1, fails. `clamp_add` is CC 3 and covered: CRAP 3.0.

## Run it

```sh
"${CLAUDE_PLUGIN_ROOT}/scripts/coverage.sh"                      # build with coverage, run tests, gcovr report, score, exit 1 on offenders
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/crap.py" build/coverage/cov.json src --top 20   # re-score an existing report
```

Settings come from `.claude/cpp-quality-gates.json` (template: `${CLAUDE_PLUGIN_ROOT}/templates/cpp-quality-gates.json`); the preset comes from `${CLAUDE_PLUGIN_ROOT}/templates/CMakePresets.quality-gates.json`. Output, worst first:

```
CRAP   15.1  CC 15  cov  92%  src/calc.cpp:24  classify( int score , bool strict , int bonus)
```

Read it as: CC says how many tests a full path cover needs, `cov` how many lines ran, CRAP what the pair costs. High CC with high cov means split; low CC with low cov means test.

## Workflow

1. Run the gate before the change to know the baseline; do not fix other people's offenders in your change.
2. Fix an offender by **splitting**: pull each branch group into a named function with one reason to change, until each piece is CC <= 8 (aim for 5), then cover each piece directly. Do not game it with a table of lambdas or by moving branches into macros; the metric measures what a reader must hold in mind.
3. Report: `CRAP: N functions touched, max <score>`.

Details, how the pipeline counts, and its limits: [references/crap.md](references/crap.md). Toolchain contract: [references/pipeline.md](references/pipeline.md).
