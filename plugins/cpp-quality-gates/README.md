# cpp-quality-gates

Make "done" mean measured for C++ projects. Four skills tell Claude when and how to run each gate; the scripts and templates they point to run on their own, without Claude.

Install: `claude plugin marketplace add wrocpp/claude-marketplace && claude plugin install cpp-quality-gates@wrocpp`

## Skills

| Skill | Use it to |
|---|---|
| `sanitizer-matrix` | run ASan + UBSan, TSan and LSan through CMake presets; know what works on macOS and Linux; run Linux checks from a Mac in a container |
| `crap-gate` | score every function with CRAP = CC^2 * (1 - cov)^3 + CC from lizard and gcovr, and split what exceeds 8 |
| `mutation-testing` | mutate one file with universalmutator, kill or triage the survivors, write the one-line `Mutation:` summary for a merge request |
| `capability-matrix` | pin the compiler features the project relies on as tiny probes run by ctest, including must-fail probes |

## Requirements

- A C++ compiler: GCC 16 is what the tests were run with; Apple clang and Homebrew clang also pass the sanitizer and capability steps. CRAP and mutation use GCC (coverage is gcov).
- On Debian and Ubuntu, clang needs `libclang-rt-dev` for the sanitizer steps: with `clang` alone even CMake's compiler check fails ("is not able to compile a simple test program"). `tests/setup.sh` installs it.
- CMake 3.23+ (presets with `include`), Ninja, Python 3.9+.
- `pip install lizard gcovr universalmutator` (gcovr 8+). `tests/setup.sh` installs them into a venv in `${XDG_CACHE_HOME:-~/.cache}/wrocpp/cpp-quality-gates-venv` (override with `QG_VENV`); `scripts/mutate.sh` makes its own venv for universalmutator.
- Docker for the Linux-container route (optional).

## Layout

```
skills/<skill>/SKILL.md          short; detail in references/
scripts/
  coverage.sh                    coverage build + tests + gcovr JSON + CRAP gate
  crap.py                        CRAP scoring of a gcovr JSON report
  mutate.py, mutate.sh           mutation harness (universalmutator)
  capability_matrix.sh           capability probes without CMake
  linux-container.sh             run a CMake preset in a Linux container
  qg_config.py                   reads .claude/cpp-quality-gates.json
templates/
  CMakePresets.quality-gates.json   coverage, asan, tsan configure/build/test presets
  CapabilityMatrix.cmake            capability_matrix() for ctest
  cpp-quality-gates.json            project settings (copy to .claude/)
  mutation_ignore.txt, mutation_triage.txt
  github-actions.yml, Dockerfile
tests/run.sh, tests/setup.sh, tests/sample/   end-to-end test on a tiny project
```

## Project settings

`.claude/cpp-quality-gates.json` (template in `templates/`) holds the roots to score, the CRAP limit, the coverage preset and gcov binary, and for the mutation harness the build directory, target names and test names. Every script also takes the same values as options; options win.

## Untrusted project input and trust model

`.claude/cpp-quality-gates.json`, the triage file and the code under test belong to whichever repository is open, so the scripts treat them as untrusted:

- **No shell.** Nothing is run with `shell=True`. A configured or command-line command (`mutation.build`, `mutation.test`, `--build`, `--test`) is split with `shlex.split` into an argument list (`qg_config.split_command`, `scripts/qg_config.py`) and refused if it contains `; | & $ ` < > ( )`, a backslash or a newline. The shell scripts quote every variable and pass lists with `set --`.
- **Validation, then refusal.** A value that reaches a command line or path must be a token (`[A-Za-z0-9_.+-]`, at most 64), a relative path (`[A-Za-z0-9_./-]`, at most 128, no `..`, no leading `/`) or an integer in range. An invalid value stops the script with exit 2 and a message that names the setting (`invalid value for coverage.preset`), never the value.
- **Never an option.** No token, name or path starts with `-` (a value like `-delete` would be read by GNU `find` as an action and delete the tree). Paths reach tools as `./`-prefixed operands, and `coverage.sh` deletes `.gcda` files only in a build directory that exists, is a directory and resolves (symlinks followed) to somewhere inside the project.
- **Fixed commands preferred.** `mutation.build_dir` with `mutation.targets` and `mutation.tests` runs `cmake --build DIR --target T...` and `ctest --test-dir DIR -R ^(names)$`; no free-form command is involved.
- **You see what runs.** `mutate.py` prints the exact argument lists it will run (`build:` and `test:` lines) and `--dry-run` prints them and stops.
- **Still your privileges.** A build and test command executes the project's code with your privileges, exactly like the project's own build. Review `.claude/cpp-quality-gates.json` of an unfamiliar repository before running the gates.
- **Output is data.** Function names print as identifiers only; a surviving mutant's source line is quoted with control characters stripped, cut to 120 characters, under a heading that says it is quoted data.
- `tests/run.sh` refuses 24 hostile configs and options (metacharacters, `$(...)`, backticks, newlines, spaces, globs, `..`, absolute paths, text where a number belongs), checks that a marker file is never created, that 46 leading-dash values (`-delete`, `--help`, `-x`, `-rf` in every setting that reaches a command) are refused with exit 2 while canary files survive, and that instruction-shaped text in a config or in source never reaches the output.

## Evidence

`sh tests/run.sh` builds the sample with the sanitizer presets and checks that planted bugs are reported, runs the CRAP pipeline and checks that the known offenders are reported and the good functions are not, runs the mutation harness with a triage file, and runs the capability probes in both directions. It exits non-zero on any failure; `WROCPP_CI=1` turns a skipped step into a failure.

| Date | Platform | Compiler | Tools | Result |
|---|---|---|---|---|
| 2026-10-18 | macOS arm64 | Homebrew GCC 16.2.0, Apple clang 21.0.0, Homebrew clang 23.1.1 | CMake 4.4.3, lizard 1.24.1, gcovr 8.7, universalmutator 1.14.1 | all checks pass; TSan skipped for GCC (does not link on macOS), LSan not run (Linux only) |
| 2026-10-18 | Linux aarch64, Docker `gcc:16` (`--security-opt seccomp=unconfined`, `WROCPP_CI=1`) | GCC 16.2.0 | CMake 3.31.6 and ninja 1.12.1 (apt), same Python tools | all checks pass including LSan and TSan |
| 2026-10-18 | Linux aarch64, Docker `gcc:16`, default seccomp | GCC 16.2.0 | same | passes; TSan reported as SKIP (cannot disable ASLR) |

MIT licensed.
