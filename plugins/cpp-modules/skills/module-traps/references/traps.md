# Trap evidence

Compiler: GCC 16.2.0 (Homebrew on macOS 26 arm64; `gcc:16` on Debian 13 aarch64). CMake: 4.4.3
(Mac), 4.4.4 (Linux). Standard C++26 unless the fixture says otherwise. Messages are from
`LC_ALL=C` builds; the runner sets that so quotes are ASCII.

`status` is the value in `expectations.json`: `reproduced` (the trap), `fixed` (its workaround builds),
`not-reproduced`, `works` (looks like a trap, is not), `behaviour` (an observable result the fixture asserts).

| Fixture | Status | Outcome | Message fragment the runner requires |
|---|---|---|---|
| `include-after-import` | reproduced | fails | `redefinition of` (`std::__terminate`, `integral_constant`, ...) |
| `c-header-after-import` | reproduced | fails | `conflicting declaration` (`struct _IO_FILE` on glibc, `__darwin_pthread_handler_rec` on macOS) |
| `include-before-import` | works | builds | |
| `macros-not-imported` | reproduced | fails | `'assert' was not declared` |
| `macros-header-before-import` | fixed | builds | |
| `coroutine-in-interface` | reproduced | fails | `Bad file data` (`failed to read compiled module cluster 2`, then `failed to load binding '::answer@co'`) |
| `coroutine-in-impl-unit` | fixed | builds | |
| `coroutine-header-with-import-std` | works | builds | a coroutine needs no `#include <coroutine>` beside `import std` |
| `contracts-inline-exported` | reproduced | fails | `__tu_has_violation` (undefined symbol at link) |
| `contracts-non-inline` | fixed | builds | |
| `contracts-no-violation-handler` | reproduced | fails | `handle_contract_violation` (undefined symbol at link) |
| `defaulted-eq-first-used-in-importer` | reproduced | crash | `internal compiler error` (Segmentation fault on macOS, reported at the struct in the interface) |
| `defaulted-eq-used-in-module` | fixed | builds | |
| `reflected-string-under-asan` | reproduced | fails | `is not a constant expression` |
| `reflected-string-no-sanitize` | fixed | builds | |
| `reflected-string-view-under-asan` | fixed | builds | |
| `add-sat-not-exported` | reproduced | fails | `'add_sat' is not a member of 'std'` |
| `format-in-constexpr` | reproduced | fails | `call to non-'constexpr' function` |
| `display-string-of-module-enum-suffix` | behaviour | builds | the program checks the value is `lib::level@lib` |
| `optional-module-type` | not-reproduced | builds | |
| `expected-module-type` | not-reproduced | builds | |
| `free-nonheap-object-braced-vector` | not-reproduced | builds | |
| `cmake-minimum-below-3-28` | reproduced | fails | `'module' does not name a type` |
| `cmake-minimum-below-3-28-scan-on` | fixed | builds | |
| `module-source-without-file-set` | reproduced | fails | ``is not found in a `FILE_SET` of type `CXX_MODULES` `` |
| `makefile-generator` | reproduced | fails | `Unsupported generator` |

## What else was tried

- **Standard headers before `import std`**: `<cwchar> <wchar.h> <string> <iostream> <cstdio> <stdio.h> <ctime>
  <locale> <cstdlib> <stdlib.h> <cstring> <string.h> <cassert> <unistd.h> <sys/types.h>` in a plain
  translation unit, and `<vector> <cwchar> <wchar.h> <string> <iostream> <cstdio> <stdio.h> <ctime>
  <locale> <cstdlib> <stdlib.h> <cstring> <sys/socket.h> <unistd.h>` in the global module fragment of a
  module interface, all built on macOS and on Debian. Headers after `import std` failed for `<cwchar>
  <wchar.h> <vector> <cstdio> <stdio.h> <cstdlib> <ctime>` on both hosts. The `__mbstate_t` conflict
  named in the original finding did not show up; the failures above are what GCC 16.2.0 prints.
- **optional / expected of a module type**: (a) one module with `struct summary { std::string plan;
  std::vector<int> quotas; }`, `constexpr std::optional<summary> parse(string_view)`, `static_assert`s that
  use `*` and `->` in the module, an importer using both at run time; (b) the same with a second module
  `b` whose `constexpr holds()` uses `*` and `->`, imported by `main`; (c) the shape in (a) with
  `std::expected<summary, failure>`. Build types: default, Debug, RelWithDebInfo and Release for (a) and (b), and Debug with
  `-fsanitize=address,undefined -O1 -D_GLIBCXX_ASSERTIONS` for (a); (c) in the default build and, as a
  fixture, on Debian. All linked and ran. Shape (b) was measured outside the fixture set; (a) and (c)
  are the fixtures.
- **A compile option on the module target only** (`-fcontracts` on the library, not on the importer)
  built and ran: no importer/module flag mismatch error was found.

## Not attempted

- A translation unit that includes stdexec crashing GCC with modules enabled: needs the stdexec sources.
- Clang: no trap was run with Clang (see the `cmake-import-std` matrix for why configure stops).
