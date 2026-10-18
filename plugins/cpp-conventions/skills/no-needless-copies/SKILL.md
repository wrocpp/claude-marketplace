---
name: no-needless-copies
description: Use BEFORE writing or reviewing C++ that passes, returns, stores, iterates or slices data - parameters, return types, range-for, substrings, callbacks, members, anything handed to another thread. Borrow with a view, transfer with a move, share shared_ptr<const T>, return by value, copy only at a nameable ownership boundary. Covers view lifetimes (which compiler diagnoses a dangling view), feature-test macros for C++23/26 facilities and the copy-smell scanner. Triggers - string_view, std::span, avoid the copy, pass by const reference, substr, dangling, std::move, copy elision, move_only_function, function_ref, copy-ok.
---

# Do not copy what you already hold

| You have | Do this |
|---|---|
| read-only use of a string or sequence | take `std::string_view` / `std::span<const T>` |
| a value the callee keeps | sink parameter: take it **by value**, then `std::move` it into place |
| immutable data many readers share | `std::shared_ptr<const T>` |
| a value you built | `return` it by value; never `return std::move(local);` |
| elements of a container in a loop | `for (const auto& x : xs)` |

**Copy only at an ownership boundary you can name**, and write the name where the copy is (a `copy-ok:` comment,
or the commit message):

1. a hand-off to another thread;
2. a callback or coroutine that outlives the call;
3. a snapshot taken before calling out (reentrancy: the callee may change the original);
4. a buffer the caller will reuse;
5. an object that must outlive its input.

A copy with no name from this list is the smell. Before writing one, look for the view, the move, the shared const.

## A view is a promise that its owner outlives it

`string_view` and `span` hold no data. Keep the owner in a named variable that outlives every use.
Measured (`references/evidence.md`): **GCC 16.2 diagnoses none of** a `string_view` from a temporary string, a
`string_view` returned from a local `std::string`, or a `span<const T>` over a temporary vector. Clang
(19 to 23, Apple 21) diagnoses all three (`-Wdangling-gsl`, `-Wreturn-stack-address`), but only as warnings, so
`-Werror` is needed to make them fail. Nothing diagnosed a view of a view of a local (`view_of_local_returned.cpp`).
A clean GCC build proves nothing about view lifetimes: build on Clang too.

## Gate library facilities on feature-test macros, never on the language version

`#include <version>` and test `__cpp_lib_move_only_function`, `__cpp_lib_function_ref`,
`__cpp_lib_ranges_to_container`. Measured: Clang 21, 22 and 23 with their own libc++, and Apple clang 21,
define neither `__cpp_lib_move_only_function` nor `__cpp_lib_function_ref`, even with `-std=c++2c`, so
`#if __cplusplus > 202302L` is not evidence that `std::function_ref` exists
(`cplusplus_version_is_not_library_support.cpp`). Clang paired with libstdc++ follows that libstdc++.
Pattern: `feature_test_gated_facilities.cpp`.

## The scanner and the hook

`hooks/pre_write_scan.py` scans the C++ text of every `Write`/`Edit`/`MultiEdit` and tells Claude about
copy smells before the file changes. It is advisory (exit 0). Rules, what each one means and what the scanner
cannot see: `references/scanner.md`. Silence a deliberate copy with
`// copy-ok: <the ownership boundary>` on the line or the line above; a marker without a reason does not count.
To block instead, put `{"copies": {"block": true}}` in `.claude/cpp-conventions.json`.

The scanner reads text. Type-aware checks (`performance-for-range-copy`,
`performance-unnecessary-value-param`) are clang-tidy's job: the separate `tidy-agent` plugin runs clang-tidy on
every edit, and this plugin does not duplicate that hook.

CLI, also usable as a guard test: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/copy_scan.py --check src/`.

## Checklist

- [ ] Parameters that only read use a view; parameters that store are sinks (by value + move).
- [ ] No `return std::move(local)`; no loop variable that copies; no `substr` on a `std::string` just to look.
- [ ] Every view has a named owner that outlives it.
- [ ] Every remaining copy names its ownership boundary.
- [ ] C++23/26 library facilities sit behind their feature-test macros.
