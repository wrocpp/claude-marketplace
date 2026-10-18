---
name: sanitizer-matrix
description: Use when setting up or running AddressSanitizer, UndefinedBehaviorSanitizer, ThreadSanitizer, LeakSanitizer or MemorySanitizer for a C++ project, when a sanitizer fails to link or hangs, when a macOS developer needs Linux-only checks, or before declaring a C++ change tested. Trigger phrases - "sanitizer", "ASan", "UBSan", "TSan", "LSan", "MSan", "-fsanitize", "data race", "heap-buffer-overflow", "use after free", "memory leak", "run in a container", "CMake preset for sanitizers".
---

# Sanitizer matrix

Run the unit tests under the sanitizer builds before calling a change done. One preset per build, because the runtimes exclude each other (ASan and TSan cannot share a binary).

| Preset | Flags | Catches |
|---|---|---|
| `asan` | `-fsanitize=address,undefined` + float, use-after-scope, `_GLIBCXX_ASSERTIONS`, pattern-initialised locals | out-of-bounds, use-after-free/scope/return, double free, signed overflow, bad shifts, null and misaligned access, float-to-int overflow; leaks on Linux |
| `tsan` | `-fsanitize=thread` | data races, lock-order inversion |
| MSan | `-fsanitize=memory`, clang only | reads of uninitialised memory; needs libc++ built with MSan too, so it is not a preset here and this plugin does not test it |

All presets add `-fno-sanitize-recover=all` so the first finding aborts the test, `-O1 -g` for usable stacks and `-fno-omit-frame-pointer`.

## Use

```sh
cp "${CLAUDE_PLUGIN_ROOT}/templates/CMakePresets.quality-gates.json" .      # or "include" it from your CMakePresets.json
CXX=g++-16 cmake --preset asan && cmake --build --preset asan && ctest --preset asan
```

The presets take the compiler from `CXX`; none is hard-coded. `${CLAUDE_PLUGIN_ROOT}/templates/github-actions.yml` runs the same on CI.

## What works where (measured with the bundled planted bugs, `tests/run.sh`)

| Platform and compiler | ASan + UBSan | LSan | TSan |
|---|---|---|---|
| macOS arm64, Homebrew GCC 16.2.0 | works | `detect_leaks=1` hangs: leave it off | does not link (`___tsan_func_entry` undefined) |
| macOS arm64, Apple clang 21.0.0 | works | aborts: "detect_leaks is not supported" | works |
| Debian, GCC 16.2.0 (`gcc:16`, aarch64) | works | works | needs `--security-opt seccomp=unconfined` |

So a macOS developer gets leak and GCC-TSan checks only on Linux: `${CLAUDE_PLUGIN_ROOT}/scripts/linux-container.sh PRESET` runs a preset in a container (sets `seccomp=unconfined` for `tsan*` presets). CI does the same, so a green Mac proves less than a green Linux job.

## Rules

- A finding is a failing test. Never `ASAN_OPTIONS=detect_leaks=0` or a suppression without a one-line reason beside it.
- Test a sanitizer's reach once: plant a bug and watch it fail (`tests/sample/tests/planted/`). A sanitizer that cannot fail proves nothing.
- UBSan's object-size check can fire before ASan on a plain `malloc` overflow (seen on Linux GCC 16.2), so the report names UBSan; hide the pointer behind `volatile` when a test must reach ASan.
- Compilers drop dead allocations: a planted leak needs a `volatile` pointer to survive `-O1`.

Containers, Docker gotchas, environment options: [references/containers.md](references/containers.md).
