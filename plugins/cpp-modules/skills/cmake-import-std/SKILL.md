---
name: cmake-import-std
description: Use when enabling `import std` in a CMake project built with GCC 16, choosing the CMAKE_EXPERIMENTAL_CXX_IMPORT_STD gate for a CMake version, or reading one of these errors - "Experimental `import std` support not enabled when detecting toolchain", "Toolchain does not support discovering `import std` support", "requires that the __CMAKE::CXX23 target exist", "unknown compiled module interface", "Unsupported generator". Trigger phrases - import std with cmake, CXX_MODULE_STD, CMAKE_EXPERIMENTAL_CXX_IMPORT_STD, which cmake version for import std, gcc 16 modules cmake, std module not found.
---

# `import std` with CMake and GCC 16

On every CMake measured (3.31.10 to 4.4.4) `import std` with GCC 16.2 still needs the experimental
gate, and the gate is a UUID that **changes between CMake releases**. A wrong UUID fails with the same
message as no UUID, so do not guess one from memory or from another project.

## Decision rule

1. `cmake --version`. Below 3.31.10, or 3.31.x before 3.31.10 (3.31.6 is what Debian 13 ships), has no
   GCC support for `import std`: install a newer CMake (`pip install "cmake>=4.0.3"` works anywhere).
2. Take the gate from the table below, or let the script find it:
   `python3 ${CLAUDE_SKILL_DIR}/../../scripts/find_import_std_gate.py --cmake cmake --cxx g++-16`
   (it tries every UUID embedded in the cmake binary in a throwaway project and prints the one that builds).
3. Set it **before `project()`** (or as `-D` / preset `cacheVariables`), then `CMAKE_CXX_MODULE_STD ON`,
   a standard of at least C++23, and the Ninja generator.

```cmake
cmake_minimum_required(VERSION 3.30)
set(CMAKE_EXPERIMENTAL_CXX_IMPORT_STD <uuid from the table>)   # before project()
project(app LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 23)            # 23 or 26; 20 does not provide the std module
set(CMAKE_CXX_MODULE_STD ON)          # targets default to CXX_MODULE_STD ON
```

The starter template's `cmake/ImportStdGate.cmake` is this table as CMake code, selected by
`CMAKE_VERSION`; copy it instead of retyping UUIDs (`modules-starter` skill).

## Gate by CMake version (GCC 16.2.0)

| CMake | Gate | Result |
|---|---|---|
| 3.30.9, 3.31.0.1, 3.31.6 | none exists | configure error: Toolchain does not support discovering `import std` support |
| 3.31.10 | `d0edc3af-4c50-42ea-a356-e2862fe7a444` | builds |
| 4.0.0 | `a9e1cf81-9932-4810-974b-6eccaf14e457` | builds |
| 4.0.3, 4.1.0, 4.1.3, 4.2.0, 4.2.3 | `d0edc3af-4c50-42ea-a356-e2862fe7a444` | builds |
| 4.3.0, 4.3.4 | `451f2fe2-a8a2-47c3-bc32-94786d8fc91b` | builds |
| 4.4.0, 4.4.3, 4.4.4 | `f35a9ac6-8463-4d38-8eec-5d6008153e7d` | builds |

Untested patch releases between these rows may carry another UUID (4.0.0 and 4.0.3 differ): run the script.
Experiments, hosts and every error text: [references/matrix.md](references/matrix.md).

## Errors and what they mean

| You see | Cause |
|---|---|
| `Experimental import std support not enabled when detecting toolchain; it must be set before CXX is enabled` | no gate, a gate of another CMake version, or the gate set after `project()` |
| `Toolchain does not support discovering import std support` | CMake too old for GCC (see rows above) |
| `fatal error: unknown compiled module interface: no such module` at the first `import std;` | gate is right but `CMAKE_CXX_MODULE_STD` is off, or the standard is 20 |
| `Unsupported generator: Unix Makefiles` | `import std` needs Ninja |
| `'module' does not name a type` in a source with a module declaration | `cmake_minimum_required` below 3.28 turns module scanning off: raise it or `set(CMAKE_CXX_SCAN_FOR_MODULES ON)` |

Standard headers before `import std;` are fine, after it they are not, and macros are not imported:
see the `module-traps` skill.

## Clang

Not measured with CMake. Homebrew LLVM 23.1.1 with `-stdlib=libc++` stops CMake at configure
(`libc++.modules.json` is not found by `clang++ -print-file-name`); see the matrix reference.
