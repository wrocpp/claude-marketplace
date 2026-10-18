# cpp26_lint rules in detail

The scanner works on a tokenised view of the file (comments and literal bodies blanked), not on a parse tree. Each rule below says what it catches and what it cannot see; the lint is advisory, so a false positive costs one allowance line and a false negative is covered by review and the compiler.

| Rule | Fires when | Does not fire / false positives | Misses |
|---|---|---|---|
| `unconstrained-template` | a `template <class T>` or `typename T` parameter, taken by a function parameter, is called (`f(...)`), awaited, used with a sink verb (`write`, `send`, `push_back`, ...), passed to `std::invoke` or forwarded and called, or the variable is named like a role (`sink`, `handler`, `callback`, ...) | a `requires` clause or a concept in place of `class`/`typename`; a type utility where `T` is only used in `sizeof` or traits. A role-named variable that is not really called can fire | a constrained-in-name-only concept; a parameter used through a lambda capture; templates declared across a macro |
| `std-include` | `#include <vector>` (any standard C++ header except `<meta>` and `<contracts>`) in a non-header file, only when `"modules": true` or the rule is switched on | C headers (`<cstdio>`, `<unistd.h>`), third-party headers; header files (`.hpp`, `.h`) are skipped because they must stay includable without modules | an include that arrives through another header |
| `legacy-io` | `<iostream>`, `std::cout/cerr/clog/cin`, `printf`/`fprintf`/`snprintf` family call | `std::print`, `std::format`; text in comments and string literals | a call through a macro or a wrapper |
| `append-chain` | three or more `x += ...;` or `x.push_back(...);` statements on one variable, back to back, inside a non-constexpr function | `constexpr`/`consteval` functions (no constexpr `std::format` on GCC 16.2); two appends; appends on different variables; appends separated by other statements | a loop that appends once per iteration |
| `string-temporary` | `std::string(1, c)` / `std::string{1, c}`, or `x += ` followed by a string literal and two or more `+` operands | one `+`, arithmetic `+=` | concatenation built across statements |
| `comment` | any comment, in a project that enabled the rule | `// Exception: <reason>` on its own line and a `}  // namespace x` closer; comment markers inside string or raw-string literals are not comments | n/a |

## Compiler notes (GCC 16.2, `-std=c++26 -freflection`)

- `std::format` is not usable in a constant expression (probe `absent/constexpr_std_format.cpp`), which is why `append-chain` leaves constexpr functions alone.
- `<meta>` is the one standard header that still sits in the global module fragment next to `import std;` in the author's project, hence the carve-out; re-check for your toolchain.
- Reflection spellings that differ from blog posts are in `skills/reflect-dont-hand-write/references/gcc-16.2-evidence.md`.
