#!/bin/sh
# Configure, build and test a CMake preset inside a Linux container: the route for macOS
# developers to LeakSanitizer, ThreadSanitizer with GCC and the glibc/libstdc++ behaviour CI sees.
#
# usage: linux-container.sh PRESET [ctest args...]     run from the project root
# env:   IMAGE (default gcc:latest; needs cmake and ninja, see templates/Dockerfile)
#        CMAKE_ARGS (extra configure arguments)
# The build goes to build/linux-PRESET so it cannot collide with a macOS configure of the same preset.
# TSan needs ptrace and mmap behaviour the default Docker seccomp profile blocks, so a preset
# whose name contains "tsan" runs with --security-opt seccomp=unconfined.
set -eu
[ $# -ge 1 ] || { echo "usage: linux-container.sh PRESET [ctest args...]" >&2; exit 2; }
preset=$1
shift
image=${IMAGE:-gcc:latest}
case $preset in *[!A-Za-z0-9_.+-]*) echo "linux-container.sh: invalid preset name" >&2; exit 2 ;; esac
case $image in *[!A-Za-z0-9_.:/@-]*) echo "linux-container.sh: invalid IMAGE" >&2; exit 2 ;; esac
case $preset in
  *tsan*) security=seccomp=unconfined ;;
  *) security=no-new-privileges=false ;;
esac
exec docker run --rm --security-opt "$security" --cap-add SYS_PTRACE --user "$(id -u):$(id -g)" \
  -e HOME=/tmp -e PRESET="$preset" -e CMAKE_ARGS="${CMAKE_ARGS:-}" \
  -e ASAN_OPTIONS=abort_on_error=1:strict_string_checks=1:detect_stack_use_after_return=1 \
  -e UBSAN_OPTIONS=print_stacktrace=1:halt_on_error=1 \
  -e TSAN_OPTIONS=halt_on_error=1:second_deadlock_stack=1 \
  -v "$PWD:/src" -w /src "$image" \
  sh -c 'command -v cmake >/dev/null && command -v ninja >/dev/null || { echo "image needs cmake and ninja: see templates/Dockerfile" >&2; exit 2; }
         set -f   # CMAKE_ARGS is split into words, never globbed
         dir=build/linux-$PRESET
         cmake --preset "$PRESET" -B "$dir" $CMAKE_ARGS && cmake --build "$dir" && ctest --test-dir "$dir" --output-on-failure "$@"' sh "$@"
