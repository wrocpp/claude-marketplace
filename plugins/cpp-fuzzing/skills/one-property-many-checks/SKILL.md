---
name: one-property-many-checks
description: Use when adding fuzz, property-based or robustness tests to C++ code, when a parser or codec needs "never crashes, round-trips" checks, or when deciding whether a function can be checked for undefined behaviour at compile time. Teaches one pure property function per module that the unit tests, the AFL++ harness, a compile-time corpus replay and a bounded-exhaustive static_assert all call, and the rule for making it constexpr. Trigger phrases: "fuzz this parser", "property test", "round trip test", "check for UB at compile time", "constexpr test", "static_assert the property", "fuzz and unit test share code".
---

# One property, many checks

Write the invariant once as a pure function of the input, then let every kind of check call it.

```cpp
constexpr bool parse_holds(std::string_view text);   // true when nothing is wrong, for ANY text
```

| Consumer | Calls it on | Finds |
|---|---|---|
| unit test | a few hand-picked inputs | regressions you thought of |
| AFL++ harness (`afl-harness` skill) | mutated bytes, at run time, under ASan and UBSan | what no one thought of |
| corpus replay (`compile-time-corpus-and-exhaustive` skill) | every corpus file, in a `static_assert` | a regression of any past finding, as a build error |
| bounded-exhaustive `static_assert` | every text up to N characters over a small alphabet | small-input defects, with no seed or luck |

The compile-time rows are the new idea: constant evaluation rejects undefined behaviour, so the
same property that returns `true` or `false` at run time also proves the absence of UB on those
inputs. A planted defect fails the BUILD while the ordinary unit tests pass
(`references/ub-evidence.md` has the table, with the fixture that produced each row).

## Writing the property

- Input is a `std::string_view` (or a span of bytes). Output is `bool`: `false` is a violated
  invariant, a crash or a compile error is UB. Rejecting bad input is a pass: `return true`.
- Say what must hold, not what the output is: round trip (`parse(format(parse(x))) == parse(x)`),
  agreement of two implementations, a recomputed total, "never throws", an idempotent normalise.
- One property per module and one function per property. A second invariant on the same module is
  a second function, because each runs in its own translation unit (see the other skill).
- The harness aborts when it returns `false`; the `static_assert` prints a message you chose.

## When the property can be constexpr

Make it `constexpr` when the code under test is pure computation on values: text in, value out. Then
write the code so constant evaluation can run it:

| Needed | Constexpr in GCC 16.2 and Clang 23 |
|---|---|
| `std::string`, `std::vector`, `std::optional`, `std::span`, `std::array`, `<algorithm>` | yes (an allocation must be freed inside the same evaluation) |
| `std::format`, `std::to_string`, iostream, `std::set`, `std::map`, `reinterpret_cast`, `memcpy`, threads, clocks, files | no: split the I/O off, keep the core pure |
| floating-point `from_chars` with a fraction | no in GCC 16.2: keep the property on integers or strings |
| a pointer-based fast path | allowed, but write it under `if consteval { portable } else { fast }` and expect only the portable branch to be checked |

A function that must touch the world stays a run-time-only property: it still gets the harness and
the sanitizers, and not the compile-time rows. Do not contort pure code to be constexpr-friendly; the
cost is usually a `constexpr` keyword and replacing `std::to_string` with a ten-line loop.

The accounting you must do: a defect on an `if !consteval` branch, or in code behind a non-constexpr
call, is invisible to the compile-time rows. The `runtime_only` fixture proves it; only ASan or
UBSan on the replay binary found that one.

## Layout and the working starter

`"${CLAUDE_PLUGIN_ROOT}/templates/fuzz-starter/"` is a complete CMake project (GCC 16, C++26, no
dependencies): a pure list parser, two property functions in `include/fuzz_starter/properties.hpp`,
one harness each, a corpus, the corpus-replay and exhaustive targets, and eight planted defects
selected by `-DFUZZ_STARTER_PLANTED_BUG=<name>`. Copy it into the project rather than reinventing the
CMake functions; `cmake/FuzzStarter.cmake` is 100 lines. Build and try a defect:

```bash
cmake -S ${CLAUDE_PLUGIN_ROOT}/templates/fuzz-starter -B build -G Ninja -DCMAKE_CXX_COMPILER=g++-16 -DFUZZ_STARTER_PLANTED_BUG=null
cmake --build build --target unit_test && build/unit_test     # passes
cmake --build build                                            # fails: dereferencing a null pointer
```

Do not plant a defect in the user's real code; use the starter to show the effect, then apply the
pattern to their module.

## Checklist when applying it to a module

1. Pick the pure core; name its property `<module>_holds`.
2. Put the property in a header both the tests and the harness include (no test framework in it).
3. Add the harness and a seed corpus (`afl-harness` skill), the corpus replay and the exhaustive
   target (`compile-time-corpus-and-exhaustive` skill).
4. Keep sanitizers off the constexpr targets and on the run-time ones.
5. When AFL++ finds something, minimise it, fix the code, and add the file to the corpus so the build
   replays it forever.
