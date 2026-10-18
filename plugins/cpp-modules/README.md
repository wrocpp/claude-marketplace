# cpp-modules

Use `import std` and named C++ modules with CMake and GCC 16 without losing hours to the traps. Three
skills, a template project and a fixture for every trap, rebuilt by the tests so a compiler or CMake
update shows up as a failure.

Install: `/plugin install cpp-modules --marketplace wrocpp/claude-marketplace`

## Skills

| Skill | Use it for |
|---|---|
| `cmake-import-std` | The `CMAKE_EXPERIMENTAL_CXX_IMPORT_STD` gate per CMake release (3.30.9 to 4.4.4 measured with GCC 16.2.0), the error each wrong setup gives, a decision rule |
| `module-traps` | Compiler crashes, link errors and include conflicts with modules, each one reproduced by a fixture with its workaround, or recorded as not reproduced |
| `modules-starter` | Copying a working project: interface and implementation unit, consumer, ctest test, host and AddressSanitizer presets |

## Requirements

- GCC 16 (16.2.0 measured). Clang with CMake `import std` was not measured past configure.
- CMake 3.31.10, or 4.0.3 and newer, and Ninja. The CMake in Debian 13 (3.31.6) and Ubuntu LTS releases
  is too old for GCC; `pip install "cmake>=4.0.3"` gives a newer one.
- Python 3 for the test runner and the gate finder. No third-party packages.

## Layout

```
.claude-plugin/plugin.json
skills/cmake-import-std/        SKILL.md, references/matrix.md (the CMake x GCC experiments)
skills/module-traps/            SKILL.md, references/traps.md (the evidence table)
skills/modules-starter/         SKILL.md
templates/modules-starter/      the starter project, with CMakePresets.json
scripts/find_import_std_gate.py prints the gate UUID that builds with the cmake and compiler given
tests/run.sh                    builds the starter and every fixture; exit 0 when all match
tests/setup.sh                  installs ninja and a newer CMake (pip wheel) in a gcc:16 container
tests/fixtures/<trap>/          one tiny CMake project per trap, and tests/fixtures/expectations.json
```

## Tests

```sh
sh tests/run.sh                  # SKIP <thing> when GCC 16, a suitable CMake or Ninja is missing
WROCPP_CI=1 sh tests/run.sh      # the same, but a missing tool is a failure
```

In a container: `docker run --rm -v "$PWD":/plugin:ro gcc:16 sh -c 'sh /plugin/tests/setup.sh && WROCPP_CI=1 sh /plugin/tests/run.sh'`.
`setup.sh` takes the CMake from the `cmake` wheel on PyPI because the distribution's is too old for
`import std` with GCC. `CXX`, `CMAKE` and `WROCPP_VENV` pick other tools.

`expectations.json` records, per fixture, whether it `builds`, `fails` (with a message fragment) or
`crash`es, its status (`reproduced`, `fixed`, `not-reproduced`, `works`, `behaviour`) and the GCC
versions it was recorded with. The runner never executes anything taken from a fixture or from
`expectations.json` other than the cmake and compiler it was told to use; fixture names and CMake
arguments are validated first.

## Licence

MIT.
