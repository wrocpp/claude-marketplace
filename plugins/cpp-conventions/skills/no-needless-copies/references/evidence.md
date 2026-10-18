# Evidence: copies and view lifetimes

Fixtures in `tests/fixtures/`, expectations in `tests/fixtures/expectations.json`, checked by
`sh tests/run.sh`. Flags: `-std=c++23 -Wall -Wextra -O2 -c` unless stated. **A** accepted without a diagnostic,
**W** warning, **R** rejected.

| id | compiler | standard library |
|----|----------|------------------|
| gcc-16 | GCC 16.2.0 | libstdc++ 16 |
| apple-clang-21 | Apple clang 21.0.0 | libc++ 22.1.6 from the macOS SDK |
| clang-21, -22, -23 | Homebrew clang 21.1.8, 22.1.8, 23.1.1 | the libc++ shipped with each (21.1.8 and 23.1.1 inspected) |
| clang-19 | Debian clang 19.1.7 in the `gcc:16` image | libstdc++ from Debian's GCC 14 |

## Dangling views

| fixture | GCC 16 | Apple clang 21 | Clang 19, 21, 22, 23 |
|---|---|---|---|
| `view_from_temporary_string` (`string_view v = std::string(...)`) | **A** | W `-Wdangling-gsl` | W `-Wdangling-gsl` |
| same, `-Werror` | A | R | R |
| `view_from_returned_string` (`string_view v = make_name()`) | **A** | W `-Wdangling-gsl` | W `-Wdangling-gsl` |
| `view_of_local_string_returned_implicitly` (`return text;` as `string_view`) | **A** | W `-Wreturn-stack-address` | W `-Wreturn-stack-address` |
| `span_over_temporary_vector` (`span<const int> s = make_values()`) | **A** | W `-Wdangling-gsl` | W `-Wdangling-gsl` |
| `view_of_local_returned` (`string_view{line}.substr(...)` of a local) | A | A | A |

GCC 16.2 at `-O2 -Wall -Wextra` is silent on all four dangling forms; the last form is silent everywhere.

## Copies the compilers do catch

| fixture | GCC 16 | Apple clang 21 | Clang 19, 21, 22, 23 |
|---|---|---|---|
| `range_for_copies_each_element` (`for (const std::string name : names)`) | W `-Wrange-loop-construct` | W | W |
| `range_for_borrows_each_element` | A | A | A |
| `return_std_move_of_local` | W `-Wpessimizing-move` | W | W |
| `return_by_value_local`, `sink_parameter_moves`, `view_param_borrows`, `shared_const_snapshot` | A | A | A |

## C++23 and C++26 library facilities

| fixture | GCC 16 | Apple clang 21 | Clang 21/22/23 (own libc++) | Clang 19 (libstdc++ 14) |
|---|---|---|---|---|
| `move_only_function_ungated` (`-std=c++23`) | A | R | R | A |
| `function_ref_ungated` (`-std=c++2c`) | A | R | R | R |
| `cplusplus_version_is_not_library_support` (`-std=c++2c`, `#error` if no `__cpp_lib_function_ref`) | A | R | R | R |
| `feature_test_gated_facilities` (`-std=c++23` and `-std=c++2c`) | A | A | A | A |

Language mode is not library support: with `-std=c++2c` every Clang above still lacks `std::function_ref`
and (with libc++) `std::move_only_function`. Gate on the macro.

Sources to cite (use the `cppreference` skill): `cpp/string/basic_string_view`, `cpp/container/span`
(borrowed ranges), `cpp/language/copy_elision`, `cpp/feature_test`.
