---
name: afl-harness
description: Use when setting up or running coverage-guided fuzzing of C++ with AFL++, building a fuzz harness that is also a replay binary, writing the Docker image for AFL++ with the GCC plugin, seeding a corpus, running a time-boxed campaign, or turning a crash into a regression corpus file. Trigger phrases: "AFL++", "afl-fuzz", "afl-g++-fast", "fuzz harness", "fuzz target", "persistent mode", "seed corpus", "crash triage", "afl-tmin", "fuzz in docker", "replay a crash".
---

# AFL++ harness, campaign and triage

The harness is a small `main` around a property from the `one-property-many-checks` skill. The same
binary is the AFL++ target and a plain replay tool, so a crash found on the fuzzing machine is
reproduced with a file argument anywhere.

Files to copy from `${CLAUDE_PLUGIN_ROOT}/templates/fuzz-starter/`:

| File | Role |
|---|---|
| `include/fuzz_starter/driver.hpp` | `run(argc, argv, property)`: replay files or directories, stdin, or AFL++ persistent mode |
| `tests/harness_<name>.cpp` | five lines: `return driver::run(argc, argv, &properties::<name>_holds);` |
| `corpus/` | seeds, then regression files |
| `ops/Dockerfile.fuzz`, `ops/fuzz.sh` | AFL++ v5.03c with the GCC plugin on `gcc:16`; a time-boxed campaign |
| `ops/triage_crashes.py` | copy crashes and hangs into the corpus under content-derived names |

## The three ways to run the same binary

```bash
build/fuzz_parse corpus/            # replay every file in a directory (ctest does this)
build/fuzz_parse < crash-file       # one input on stdin
afl-fuzz -i corpus -o out -m none -- build/fuzz_parse    # built with afl-g++-fast: persistent mode, no @@
```

- A failing property calls `std::abort()`; AFL++ records `sig:06`. A sanitizer report precedes it.
- Persistent mode (`__AFL_LOOP`) gave 154,000 execs per second on this harness in `gcc:16`
  (AFL++ 5.03c, 8 cores, 10 s run); plain `@@` file mode is much slower.
- The persistent macros are GNU statement expressions and name globals of the AFL runtime, so
  `driver.hpp` expands them in a global-scope function, and the CMake file adds `-Wno-pedantic` when
  the compiler is an `afl-*` wrapper.
- Copy the case into an exact-size `std::vector` before calling the property: AFL++'s shared
  buffer is a megabyte, and ASan cannot see a read past the end of a case inside it.
- `replay` returns non-zero when it found no files, so an empty or misspelled corpus path fails
  the test instead of passing vacuously.

## Docker recipe

`ops/Dockerfile.fuzz`: `FROM gcc:16`, apt-install `cmake ninja-build git make python3`, clone AFL++
(`AFLPP_REF` build argument, default `v5.03c`), `make source-only NO_NYX=1 NO_PYTHON=1 NO_SPLICING=1`,
`make install PREFIX=/usr/local`. `afl-cc -h` then shows `[GCC_PLUGIN] ... AVAILABLE [SELECTED]`; the
image needs no LLVM. The project is mounted at `/src`, built with `-DCMAKE_CXX_COMPILER=afl-g++-fast`.

`ops/fuzz.sh <target> [seconds] [planted-bug]` builds the image, builds only `fuzz_<target>` with
`AFL_USE_ASAN=1 AFL_USE_UBSAN=1` (do not also pass `-fsanitize`), runs `afl-fuzz -V <seconds>` and
lists `crashes/` and `hangs/`. It checks the target and the planted-bug name (lowercase letters and underscores) and the seconds
(digits) before they reach the container shell, and refuses a target with no `tests/harness_<target>.cpp`.

Environment that matters inside a container: `AFL_SKIP_CPUFREQ=1` (no governor to read),
`AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES=1` (no `core_pattern` control), `AFL_NO_UI=1` (no terminal),
`ASAN_OPTIONS=abort_on_error=1:symbolize=0:detect_leaks=0`, `UBSAN_OPTIONS=halt_on_error=1:abort_on_error=1`,
and `-m none` on `afl-fuzz` (ASan reserves huge address space). Run as the host user with `--user`
so `build/fuzz/findings` is not owned by root.

## Seed corpus

- Start with 5 to 20 small files: one valid, one per grammar branch, the empty file, the extremes of
  each numeric field, and one that is mostly junk. The starter has `few`, `extremes`, `top`, `one_negative`,
  `too_big`, `forty`, `empty` and `junk` (non-UTF-8 bytes).
- Keep each seed small; AFL++ mutates bytes, not structure, and large seeds slow it.
- The same files feed the compile-time replay, so a seed that triggers UB in the code is a build error.
- A dictionary (`-x tokens.dict`) with the format's delimiters and keywords helps text formats a lot.

## A time-boxed campaign

1. Pick the budget before starting: 60 s as a smoke test in CI, 10 to 60 minutes locally, hours
   nightly. Say it in the report: `afl-fuzz -V 30`.
2. Run `ops/fuzz.sh parse 30` (or the commands above). Success is `saved_crashes : 0` in
   `findings/<name>/default/fuzzer_stats` and a corpus count that grew, not the absence of output.
3. Report the numbers: `execs_done`, `corpus_count`, `saved_crashes`, `saved_hangs`, the AFL++ and
   compiler versions. A short campaign finding nothing is not a proof; the starter's planted
   `runtime_only` defect was found in 4 ms of a 30 s run (7 crash files, one root cause; `references/campaign-evidence.md`).

## Triage a crash into the regression corpus

1. Reproduce: `build/fuzz_parse 'findings/parse/default/crashes/id:000000,...'` with the sanitized
   build; read the ASan or UBSan report, not just the abort.
2. Minimise (inside the AFL++ image): `afl-tmin -i crash -o small -m none -- build/fuzz_parse @@`.
   Several crash files often share one root cause.
3. Fix the code, or the property if the property was wrong.
4. `python3 -I ops/triage_crashes.py findings/parse corpus` copies each crash and hang to
   `corpus/crash-<sha256 prefix>` and `hang-...`; it is idempotent, skips files over 1 MiB, never
   follows symlinks and never uses a name from the findings directory as a path.
5. Rebuild: the corpus-replay target now proves the fix at compile time, and `ctest` replays it under
   the sanitizers. A crash that came from a run-time-only branch fails the sanitized replay, not the
   compile-time replay, which is expected.
6. Commit the fix and the corpus files together.

## Not covered here

Structure-aware fuzzing (libprotobuf-mutator), libFuzzer, and sanitizers beyond ASan and UBSan.
MSan is the tool for an uninitialised read that the compile-time check did not reach; it needs Clang.
