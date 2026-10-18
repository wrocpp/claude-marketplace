# Evidence for the AFL++ recipe

Run on 2026-10-18, Docker `gcc:16` (GCC 16.2.0, Debian 13, aarch64) via Colima on macOS, AFL++ v5.03c
built by `templates/fuzz-starter/ops/Dockerfile.fuzz`.

| Claim | Command | Result |
|---|---|---|
| The harness builds with `afl-g++-fast` and persistent mode works | `afl-fuzz -i corpus -o out -m none -V 10 -- build/fuzz_parse` | `target_mode: persistent shmem_testcase deferred`, 1,540,217 execs, 153,990 execs/s, corpus 8 to 54 |
| The binary still replays | `build/fuzz_parse corpus` | `replayed 8 inputs` |
| A planted run-time-only defect is found | `ops/fuzz.sh parse 30 runtime_only` (ASan and UBSan on) | 7 crash files within 30 s; first at 4 ms |
| Triage is idempotent | `triage_crashes.py findings corpus`, twice | 7 added, then 0 |
| The plugin's `tests/run.sh` passes with AFL++ present | `docker run ... fuzz-starter-afl sh tests/run.sh` with `WROCPP_CI=1` | AFL++ line passes |

`tests/run.sh` treats AFL++ as optional: without `afl-fuzz` the line is `SKIP AFL++ not installed
(optional)`, also under `WROCPP_CI=1`.
