---
name: modules-starter
description: Use when starting a new C++ project or library that uses named modules and `import std` with CMake and GCC 16, or when adding a module interface unit, an implementation unit or a module test to one. Copies a working template with the gate, a module with an interface and an implementation unit, a consumer, a ctest test and CMake presets for a host and an AddressSanitizer build. Trigger phrases - new modules project, cmake modules template, module interface and implementation unit, set up import std project, FILE_SET CXX_MODULES example.
---

# Modules starter

`${CLAUDE_PLUGIN_ROOT}/templates/modules-starter/` builds and passes with GCC 16.2 and CMake 4.4 on macOS and in
the `gcc:16` image; `tests/run.sh` rebuilds it with both presets.

```
CMakeLists.txt            gate, standard, FILE_SET CXX_MODULES, executable, test
CMakePresets.json         host (RelWithDebInfo) and asan (Debug, address and undefined sanitizers)
cmake/ImportStdGate.cmake the CMake-version -> gate table (cmake-import-std skill)
src/greeter/greeter.cppm  export module starter.greeter: constexpr code, a declaration
src/greeter/greeter.cpp   module starter.greeter; the definition (implementation unit)
app/main.cpp              consumer: import starter.greeter; import std;
tests/greeter_test.cpp    ctest test without a framework
```

Use it:

```sh
cp -R "${CLAUDE_PLUGIN_ROOT}/templates/modules-starter" my-project && cd my-project
CXX=g++-16 cmake --preset host && cmake --build --preset host && ctest --preset host
CXX=g++-16 cmake --preset asan && cmake --build --preset asan && ctest --preset asan
```

Choose the compiler with `CXX` (the presets do not name one). `-DSTARTER_CXX_STANDARD=26` builds as C++26.

Conventions the template follows, each tied to a measured trap (`module-traps` skill):

- one module per library, its interface in `target_sources(... PUBLIC FILE_SET CXX_MODULES BASE_DIRS src FILES ...)`
  and the implementation unit as a `PRIVATE` source;
- functions with bodies that need a coroutine or contracts are declared in the interface and defined in
  the implementation unit;
- `import std;` in every unit, standard headers only before it, macros through their header;
- tests are executables that `import` the module and are registered with `add_test`.

Rename `starter` and `greeter` everywhere (target, module name, directory); the module name is the
`export module` line, the file name does not matter to CMake.
