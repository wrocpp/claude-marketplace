---
name: capability-matrix
description: Use when a C++ project depends on compiler or library features that are new, experimental or version-sensitive (C++26 reflection, contracts, modules, import std, coroutines, a standard library facility), when a compiler upgrade must be detected, or when recording which workarounds can be removed. Trigger phrases - "does this compiler support", "feature test", "capability probe", "compiler upgrade broke", "newest gcc", "workaround for missing feature", "must-fail test", "feature-test macro".
---

# Capability matrix

For every compiler feature the project relies on, keep one tiny translation unit that uses only that feature. Run them as tests. Then a compiler or library change shows up as one named red test, not as a mystery in the main build, and the workaround for a missing feature has an alarm that rings when it can go.

```
tests/capabilities/
  supported/structured_bindings.cpp   must compile
  absent/static_reflection.cpp        must NOT compile (today)
```

```cmake
include(templates/CapabilityMatrix.cmake)
capability_matrix(DIR tests/capabilities FLAGS -std=c++20)   # ctest -L capability
```

Without CMake: `scripts/capability_matrix.sh COMPILER DIR [FLAGS...]` (prints `ok`/`FAIL` per probe, exit 1 on any surprise).

## Rules

- One feature per file, named by the feature (`annotated_member_function_dispatch.cpp`), not by the bug. The file is the whole evidence; no comment needed beyond what a reader cannot see.
- `supported/` pins what you rely on. `absent/` pins what you work around: it fails to compile today, and the day a compiler accepts it, the test (CMake `WILL_FAIL`) goes red and says the workaround can be removed.
- Probes are `-fsyntax-only`: they prove the front end accepts the spelling, not that code generation or linking works. Put run-time behaviour in unit tests.
- Gate on the feature, not the version: a probe may `#ifndef __cpp_...` / `#error` to document the feature-test macro it expects.
- Run the matrix on the pinned compiler in CI and on the newest released one nightly (`templates/github-actions.yml`, job `capabilities-newest-gcc`).
- Bump nothing without the matrix: a compiler upgrade is a green matrix plus the main build.

## Evidence

The bundled sample (`tests/sample/tests/capabilities`) passes under GCC 16.2.0, Apple clang 21.0.0 and Homebrew clang 23.1.1 in C++20 mode: 2 supported probes compile, 1 absent probe (`__cpp_impl_reflection` is undefined) fails to compile. `tests/run.sh` also checks the failure direction: a broken supported probe and an absent probe that compiles both fail the matrix.
