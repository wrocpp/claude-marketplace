# Measurements: CMake x GCC for `import std`

## Method

A project of one file, `import std; int main() { std::println(...); }`, was configured with
`-G Ninja`, built and run, for each CMake in turn. The CMake builds came from the PyPI `cmake` wheels
(one virtual environment per version) and from Homebrew; each wheel ships the official binary.
`scripts/find_import_std_gate.py` collects every UUID found in the cmake executable and repeats the
configure and build with each as `CMAKE_EXPERIMENTAL_CXX_IMPORT_STD`.

| Host | Compiler | Notes |
|---|---|---|
| macOS 26 arm64 | Homebrew GCC 16.2.0 | CMake 3.30.9 to 4.4.4 |
| Debian 13 aarch64, `gcc:16` image | GCC 16.2.0 | CMake 4.4.4 (wheel) and the distribution's 3.31.6 |

On Linux only CMake 4.4.4 (wheel) and 3.31.6 (distribution) were run; the rest of the table is from
the Mac. CMake releases that were not measured: 3.30.0 to 3.30.8, 3.31.1 to 3.31.5, 3.31.7 to 3.31.9, 4.0.1,
4.0.2, 4.1.1, 4.1.2, 4.2.1, 4.2.2, 4.3.1 to 4.3.3, 4.4.1 and 4.4.2, so a UUID can differ there.

## Gate that builds, per CMake release (GCC 16.2.0, standard 23 and 26)

| CMake | Gate | Result |
|---|---|---|
| 3.30.9 | none | configure error, no GCC support |
| 3.31.0.1 | none | configure error, no GCC support |
| 3.31.6 | none | configure error, no GCC support (also Debian's apt package, in `gcc:16`) |
| 3.31.10 | d0edc3af-4c50-42ea-a356-e2862fe7a444 | builds, runs |
| 4.0.0 | a9e1cf81-9932-4810-974b-6eccaf14e457 | builds, runs |
| 4.0.3 | d0edc3af-4c50-42ea-a356-e2862fe7a444 | builds, runs |
| 4.1.0, 4.1.3 | d0edc3af-4c50-42ea-a356-e2862fe7a444 | builds, runs |
| 4.2.0, 4.2.3 | d0edc3af-4c50-42ea-a356-e2862fe7a444 | builds, runs |
| 4.3.0, 4.3.4 | 451f2fe2-a8a2-47c3-bc32-94786d8fc91b | builds, runs |
| 4.4.0, 4.4.3, 4.4.4 | f35a9ac6-8463-4d38-8eec-5d6008153e7d | builds, runs |

CMake 4.4.4, the newest measured, still needs the gate. The CMake manual of 4.4.4 lists "GCC 15 and
newer" for `import std` and still describes the support as experimental.

## Wrong setups and the first error they give

Each row was run on CMake 3.31.10, 4.0.3, 4.1.3, 4.2.3, 4.3.4 and 4.4.3 unless noted.

| Setup | Stage | Result |
|---|---|---|
| `CMAKE_CXX_MODULE_STD ON`, no gate | configure | `The "CXX_MODULE_STD" property on the target "p" requires that the "__CMAKE::CXX23" target exist, but it was not provided by the toolchain. Reason: Experimental import std support not enabled when detecting toolchain; it must be set before CXX is enabled (usually a project() call)`. From 4.3 the first sentence reads `requires toolchain support, but it was not provided`. |
| gate of another CMake release | configure | the same message as no gate (so the message does not say the UUID is wrong) |
| gate set after `project()` (4.4.3) | configure | the same message |
| gate as `-DCMAKE_EXPERIMENTAL_CXX_IMPORT_STD=...` (4.4.3) | builds | works: a cache entry counts as set before `project()` |
| gate right, `CMAKE_CXX_MODULE_STD` off | build | `main.cpp:1:1: fatal error: unknown compiled module interface: no such module` |
| gate right, C++20 | build | 3.31.10 to 4.3.4: the same `unknown compiled module interface`; 4.4.3: `'println' is not a member of 'std'` |
| gate right, `CMAKE_CXX_EXTENSIONS ON` (4.4.3) | builds | works (`-std=gnu++26`) |
| gate right, `-G "Unix Makefiles"` | configure | 4.4.3: `Reason: Unsupported generator: Unix Makefiles`; 3.31.10 to 4.2.3: the generic `__CMAKE::CXX26 target exist` error |
| any gate, CMake 3.30.9 | configure | `Toolchain does not support discovering import std support` |
| `cmake_minimum_required(VERSION 3.26)`, module sources | build | `error: 'module' does not name a type`: policy CMP0155 is off, nothing is scanned. `set(CMAKE_CXX_SCAN_FOR_MODULES ON)` fixes it. Fixtures `cmake-minimum-below-3-28*` |
| module unit in `add_library(lib lib.cppm)` without a `FILE_SET CXX_MODULES` | build | `CMake Error: Output ... provides the lib module but it is not found in a FILE_SET of type CXX_MODULES`. Fixture `module-source-without-file-set` |

## Clang

Homebrew LLVM 23.1.1, `-stdlib=libc++`, CMake 3.31.10 and 4.4.3, with and without
`-L/opt/homebrew/opt/llvm/lib/c++`:

- 3.31.10: `Reason: libc++.modules.json resource does not exist`
- 4.4.3: `Failed to load C++ standard library modules metadata from "libc++.modules.json": File not found`

`clang++ -stdlib=libc++ -print-file-name=libc++.modules.json` prints the bare name although the file is
in `lib/c++/`. Nothing past configure was measured with Clang, so no Clang result is claimed.
