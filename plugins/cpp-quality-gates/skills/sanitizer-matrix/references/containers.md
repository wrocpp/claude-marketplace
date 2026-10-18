# Linux in a container, and runtime options

## Route for macOS developers

```sh
IMAGE=gcc:16 scripts/linux-container.sh asan   # default image is gcc:latest
scripts/linux-container.sh tsan -R race    # arguments after the preset go to ctest
```

The script mounts the working tree at `/src`, runs as your uid, and needs `cmake` and `ninja` in the image: build it from `templates/Dockerfile` (`docker build -t qg templates && IMAGE=qg scripts/linux-container.sh asan`). The build goes to `build/linux-<preset>` in your tree, apart from a macOS configure of the same preset.

## Gotchas

| Symptom | Cause | Fix | Seen |
|---|---|---|---|
| `FATAL: ThreadSanitizer: encountered an incompatible memory layout but was unable to disable ASLR` (exit 66) | the default Docker seccomp profile blocks `personality(ADDR_NO_RANDOMIZE)` | `--security-opt seccomp=unconfined` | `gcc:16`, aarch64, in this plugin's tests |
| LeakSanitizer reports nothing in a leaking test | the compiler removed the dead allocation | keep the pointer in a `volatile` | same |
| LeakSanitizer cannot run as non-root | ptrace is needed to stop the process at exit | `--cap-add SYS_PTRACE` | the script sets it; root in the test needed none |
| Homebrew GCC on macOS: TSan link error | libtsan is not shipped for that target | use Apple/Homebrew clang for TSan locally, GCC in Linux CI | `___tsan_func_entry` undefined |
| `detect_leaks=1` spins at 100% CPU on macOS GCC | LeakSanitizer is not implemented for the target | do not set it on macOS | measured: killed after 10 s |

Not verified here (reported by others, check on your runner before relying on it): newer kernels with a high `vm.mmap_rnd_bits` make TSan abort at start on some CI images; lowering it with `sysctl vm.mmap_rnd_bits=28` is the usual fix.

## Environment options worth setting

`ASAN_OPTIONS=abort_on_error=1:strict_string_checks=1:detect_stack_use_after_return=1`, `UBSAN_OPTIONS=print_stacktrace=1:halt_on_error=1`, `TSAN_OPTIONS=halt_on_error=1:second_deadlock_stack=1`. The template test presets set them, so `ctest --preset asan` applies them; a plain `ctest --test-dir` does not.

## Compile-time evaluation

Code that is evaluated at compile time is not sanitised, and sanitizer flags can make constant evaluation fail (`is not a constant expression` for pointers from `define_static_string`, seen by the author on GCC 16.2, not re-run here). Give constexpr-only test targets `-fno-sanitize=all`. The compile-time check is stronger than any sanitizer for that code: constant evaluation rejects out-of-bounds reads, signed overflow and uninitialised reads as errors.
