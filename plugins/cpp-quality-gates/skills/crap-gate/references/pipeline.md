# Pipeline contract

| Script | Input | Output | Exit |
|---|---|---|---|
| `scripts/coverage.sh [-c CONFIG] [-p PRESET] [-g GCOV] [-b BUILD_DIR] [-j JSON] [--no-gate]` | a CMake project with a `coverage` preset | `<build_dir>/cov.json`, offenders on stdout | 0 clean, 1 offenders, other = build or test failure |
| `scripts/crap.py COVERAGE_JSON [ROOTS...] [--max N] [--top N] [--missing zero\|covered] [--config FILE]` | gcovr JSON, source roots | one line per offender (or per worst `--top` function) and a count | 0 clean, 1 offenders, 2 lizard missing |

Config (`.claude/cpp-quality-gates.json`, section `crap` and `coverage`): `roots`, `max`, `suffixes`, `preset`, `build_dir`, `gcov`, `filters`. Options win over the file; the file wins over the defaults (`src`, 8, preset `coverage`, `build/<preset>`, `gcov`).

Requirements: CMake 3.23+, Ninja, a GCC with its matching `gcov`, `pip install lizard gcovr` (gcovr 8 or newer: the script passes `--gcov-ignore-errors=no_working_dir_found` for the compiler-probe files CMake builds).

CI: `templates/github-actions.yml` job `crap`.
