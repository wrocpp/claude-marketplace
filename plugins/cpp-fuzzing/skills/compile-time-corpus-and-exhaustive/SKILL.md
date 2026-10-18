---
name: compile-time-corpus-and-exhaustive
description: Use when turning fuzz corpus files or small-input enumeration into build-time checks in C++, with #embed and static_assert. Covers corpus replay via #embed, bounded-exhaustive generation over a small alphabet, the constexpr budget flags (-fconstexpr-ops-limit, -fconstexpr-loop-limit, Clang -fconstexpr-steps), memory and out-of-memory limits, one translation unit per property, shallow versus deep depth, and why these targets turn sanitizers off. Trigger phrases: "#embed", "static_assert the corpus", "exhaustive test at compile time", "constexpr ops limit", "constexpr evaluation operation count exceeds limit", "compile out of memory", "for_all_texts", "narrowing conversion embed", "regression corpus in the build".
---

# Corpus replay and bounded-exhaustive checks at compile time

Both targets are a generated `.cpp` whose only content is `static_assert`s of a property from the
`one-property-many-checks` skill. A violated property, or any undefined behaviour on the way, is a
compile error. The working code is `${CLAUDE_PLUGIN_ROOT}/templates/fuzz-starter/cmake/FuzzStarter.cmake`
(`fuzz_starter_constexpr_corpus`, `fuzz_starter_constexpr_exhaustive`) with
`include/fuzz_starter/embedded.hpp` and `exhaustive.hpp`.

## Corpus replay with #embed

```cpp
constexpr unsigned char file_0[] = {
#embed "/abs/path/corpus/few"
};
static_assert(embedded_holds<&properties::parse_holds>(file_0), "corpus replay: few");
```

- GCC 15+ and Clang accept `#embed` in C++26 mode. Clang warns `-Wc23-extensions`; the template
  turns that off for the corpus target only.
- Embed as `unsigned char`. Into `char[]`, a byte of `0x80` or more is
  `error: narrowing conversion of '255' from 'int' to 'char'` (GCC 16.2). `embedded_holds` copies the
  bytes into a `std::vector<char>` of exactly the file's size.
- An empty file gives an empty initialiser, which cannot declare an array: assert
  `property(std::string_view{})` for it instead (CMake `file(SIZE ...)` decides).
- Generate the file at configure time with `file(GENERATE)` over `file(GLOB CONFIGURE_DEPENDS ...)` and
  set `OBJECT_DEPENDS` to the corpus files, so a new crash file reruns the check.
- A path or label that reaches generated C++ is checked first (`fuzz_starter_require_plain`): a quote,
  backslash or newline stops the configure.

The corpus is where seeds and past crashes live, so every defect AFL++ ever found is re-proved on
every build. Prefer this to a hand-written regression test per crash.

## Bounded-exhaustive generation

```cpp
static_assert(for_all_texts(R"alpha(0-,9)alpha", 4, &properties::parse_holds), "a short text breaks parse_list");
```

Every text of length 0..N over the alphabet, in order. Choose the alphabet by what the grammar
distinguishes: its delimiters, one digit, one letter, a sign, an escape character, a byte above 0x7f.
Four characters at length 4 is 341 texts; the count is `(a^(N+1)-1)/(a-1)`.

Build each text in a `std::vector<char>` of exactly its size (`for_all_texts` does). A `std::string`
keeps a NUL after the last character, so a raw `data()[size()]` read passes the check; see
`one-property-many-checks/references/ub-evidence.md`.

## The budget

GCC stops a constant evaluation by operation count and loop iterations; the error names the flag.
Measured on `parse_holds` over `0-,9` (GCC 16.2.0, `-O0`, macOS arm64, one `static_assert`):

| Length | Texts | Default limits | Raised limits | Peak memory |
|---|---|---|---|---|
| 4 | 341 | ok, 0.4 s | ok | 137 MB |
| 5 | 1365 | ok, 0.7 s | ok | 185 MB |
| 6 | 5461 | `'constexpr' evaluation operation count exceeds limit of 33554432 (use '-fconstexpr-ops-limit=' to increase the limit)` | 1.9 s | 373 MB |
| 7 | 21845 | same error | 6.3 s | 1.2 GB |
| 8 | 87381 | same error | 24.7 s | 1.4 GB |

- `-fconstexpr-ops-limit=4000000000` and `-fconstexpr-loop-limit=100000000` (the template's values).
  The single-loop default is 262144: `'constexpr' loop iteration count exceeds limit of 262144 (use '-fconstexpr-loop-limit=' to increase the limit)`.
  Clang's one knob is `-fconstexpr-steps=`; at length 6 it says `constexpr evaluation hit maximum step limit; possible infinite loop?`.
- Time and memory grow about four times per extra character here. A check that is fine at 1 GB on a
  laptop is an out-of-memory kill on a small CI runner, and the kill looks like a compiler crash.
- One translation unit per property (the template does this), because a TU holding several
  exhaustive checks adds their memory, and with several compile jobs in parallel the sum is what
  the machine sees. The template also puts these targets in a Ninja job pool of two
  (`JOB_POOL_COMPILE`); lower it on small machines.
- Two depths: `-DFUZZ_STARTER_DEPTH=shallow` for every build, `deep` (two more characters here) for a
  nightly or release job. Pick shallow so that a developer machine builds it in seconds.
- Use `-O0`. Optimisation does not speed up constant evaluation and costs compile time.

## Why these targets disable sanitizers

`-fno-sanitize=all` on the constexpr targets: nothing runs, so there is nothing to sanitise, and the
instrumented compile pays for work it cannot use. A larger project reported an instrumented constexpr
corpus target failing with `(const char*)(&"ok") == 0 is not a constant expression`. The starter did not
reproduce a difference in GCC 16.2 (it builds with and without instrumentation), so treat this as
precaution, not as a measured necessity. Run the sanitizers on the unit test and the harness
(`-DFUZZ_STARTER_SANITIZE=ON`), where they find real things.

## Pitfalls that cost time

- The library has to be constexpr end to end: `std::format`, `std::to_string`, `std::set`, `std::map`
  and `reinterpret_cast` stop the evaluation. Say so in the module, not in a comment.
- A defect on an `if !consteval` branch is not evaluated.
- Overflow and shift defects need a long enough input; the exhaustive bound will not reach them, the
  corpus has to.
- Do not add `-fpermissive` to these targets: it turns `overflow in constant expression` into a
  warning, though the `static_assert` still fails on GCC 16.2.
