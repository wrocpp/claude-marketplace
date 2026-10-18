---
name: module-traps
description: Use when C++ modules or `import std` misbehave with GCC 16 and CMake - a compiler crash (internal compiler error), "Bad file data" or "failed to read compiled module cluster", "failed to load binding", link errors for __tu_has_violation or handle_contract_violation, "redefinition" or "conflicting declaration" after `import std`, "'assert' was not declared", "'module' does not name a type", "provides the module but it is not found in a FILE_SET", or before writing an exported coroutine, an exported inline function with contracts, a defaulted operator== on an exported struct, or a constexpr std::string from a reflected name. Trigger phrases - module build fails, import std include conflict, export module crash, std::optional link error module, add_sat, std::format constexpr.
---

# Traps with C++ modules, GCC 16 and CMake

Every row below is a fixture under `${CLAUDE_SKILL_DIR}/../../tests/fixtures/<name>/` that
`sh ${CLAUDE_SKILL_DIR}/../../tests/run.sh` builds and compares with `tests/fixtures/expectations.json`.
Results are for **GCC 16.2.0**, macOS arm64 (Homebrew) and Debian 13 (`gcc:16`), CMake 4.4.x. A trap
that did not reproduce is listed as such: do not "fix" what you cannot show.

## Before writing module code

- **Standard headers go before `import std;`, never after.** `import std; #include <vector>` fails
  with `redefinition of 'void std::__terminate()'`; a C header (`<stdio.h>`) fails with
  `conflicting declaration 'struct _IO_FILE'`. Includes before `import std;`, or in the global module
  fragment of a module unit, build. Fixtures `include-after-import`, `c-header-after-import`,
  `include-before-import`.
- **Macros are not imported.** `assert` and `stderr` need their header, placed before
  `import std;` (`macros-not-imported`, `macros-header-before-import`).
- **An exported non-template coroutine must not have its body in the interface.** Importers fail with
  `failed to read compiled module cluster 2: Bad file data`. Declare it in the interface, define it in
  an implementation unit (`coroutine-in-interface`, `coroutine-in-impl-unit`).
- **Contracts: not on an exported inline function.** The link fails with undefined
  `__tu_has_violation`. Put the `pre()` on the non-inline declaration in the interface and the body in
  an implementation unit, without repeating the contract (`contracts-inline-exported`,
  `contracts-non-inline`). libstdc++ 16.2 also has no default `handle_contract_violation`; define it
  once (`contracts-no-violation-handler`).
- **A defaulted `operator==` on an exported struct crashes GCC** (`internal compiler error`) when its
  first use is in an importing file. Use it once inside the module, for example in a `static_assert`
  (`defaulted-eq-first-used-in-importer`, `defaulted-eq-used-in-module`).
- **A `constexpr std::string` built from a reflected name fails under `-fsanitize=address`** with
  `'(const char*)(&"ok") == 0' is not a constant expression`. Return `std::string_view`, or compile
  that target with `-fno-sanitize=all` (`reflected-string-under-asan`, `reflected-string-no-sanitize`,
  `reflected-string-view-under-asan`).
- **Not in `import std` / not constexpr on 16.2:** `std::add_sat` (`add-sat-not-exported`),
  `std::format` in a constant expression (`format-in-constexpr`).
- `std::meta::display_string_of` of an enum declared in a module ends in `@module`
  (`lib::level@lib`; fixture `display-string-of-module-enum-suffix`).
- CMake: `cmake_minimum_required` below 3.28 does not scan for modules, a module unit must be in a
  `FILE_SET CXX_MODULES`, the generator must be Ninja (fixtures `cmake-minimum-below-3-28`,
  `module-source-without-file-set`, `makefile-generator`; `cmake-import-std` skill).

## Reported once, not reproduced

`constexpr` functions returning `std::optional<T>` / `std::expected<T, E>` of a module type, called at
run time from another translation unit, were reported to leave `operator*` / `operator->` undefined at
link time; the explicit instantiation `template class std::optional<T>;` was the workaround. Three shapes
(optional in one module, optional through a second module, expected in one module) linked in the default,
Debug, RelWithDebInfo and Release builds, the first also with sanitizers: NOT REPRODUCED on 16.2.0. The same for `-Wfree-nonheap-object` on a braced `vector<pair<string,string>>`
at -O2 (`free-nonheap-object-braced-vector`). A stdexec translation unit crashing the compiler was
not attempted (it needs the stdexec sources). Evidence and the exact shapes tried:
[references/traps.md](references/traps.md).

## Working on a trap

Reproduce it as a fixture first (`tests/run_fixtures.py --observe --only <name>` prints what the
compiler does), record the outcome in `expectations.json` with the compiler version, then fix.
