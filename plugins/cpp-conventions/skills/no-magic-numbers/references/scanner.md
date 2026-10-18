# The bare-number scanner

`scripts/number_scan.py` (stdlib Python). It blanks comments, string and character literals and preprocessor
lines, finds every numeric literal, and reports those that are not exempt. Output: `line: [numbers] bare number N: ...`.
CLI: `number_scan.py [--check] [--allow N] PATH...` (a directory is scanned recursively for C++ files).

## Exempt, exactly

| what | example |
|---|---|
| the values 0 and 1, any spelling | `0`, `0u`, `0x0`, `1.0f`, `-1`, `1s` (`1'000` has the value 1000 and is reported) |
| 100 on a line containing `%`, `percent` or `pct` | `part * 100 / whole` is not exempt unless the line says percent; the C `%` operator counts as a `%` |
| comments, string and character literals, raw strings | `// retry 7 times`, `"port 8080"` |
| preprocessor lines | `#if __cplusplus >= 202302L`, `#define LIMIT 42` |
| the initializer of a `constexpr`, `consteval`, `constinit` or `const` definition, also `static`, `inline`, `extern`, `thread_local` and `template<...>` prefixed | `static constexpr auto kTimeout = 30s;`, `constexpr Options o{.width = 80};` |
| enumerators | `enum class Color { Red = 5 }` |
| a template parameter default | `template <int N = 8> struct B;` |
| `static_assert(...)` | `static_assert(sizeof(int) == 4)` |
| the index of `get<N>`, `tuple_element<N`, `variant_alternative<N`, `in_place_index<N>` | `std::get<2>(t)` |
| numbers in the `numbers.allow` list of `.claude/cpp-conventions.json` | `{"numbers": {"allow": [2, 8]}}` |
| arguments of `EXPECT_*`, `ASSERT_*`, `CHECK*`, `REQUIRE*` and `assert(` **in test files** (a path part named `test`/`tests`/`spec`, or a name ending `_test`/starting `test_`) | `EXPECT_EQ(total(), 42)` |
| a line (or the line after a comment line) with `magic-ok: <reason>` | `// magic-ok: RFC 9110 default port` |

## Reported

Everything else, including: array sizes (`int buf[16]`), default member initializers that are not `constexpr`
(`int n = 3;`), default arguments (`f(int retries = 3)`), `case 3:`, loop bounds, `x * 2`, exit codes
(`return 2;`), literals with unit suffixes outside a definition (`30s`), floating-point constants (`3.14`),
hex masks (`0xFF`).

## Does not catch

- A literal spelled with a macro or built by arithmetic on exempt values (`1 + 1`, `1 << 10` reports only 10).
- A number inside a string meant as a number (`"4096"` passed to `std::stoi`), or in a comment-only specification.
- Numbers in other languages: CSS, JSON, shell, CMake. Run the same idea with a stylelint or a grep gate there.
- A *named* constant that is itself a guess with no source: the scanner checks that the number has a name,
  not that the comment beside it is true.
- Code the tokenizer cannot parse (unbalanced braces in a pasted snippet are tolerated, but a statement can then
  be classified wrongly, e.g. a `constexpr` that started before the snippet).

## Tests

`tests/test_scripts.py` (`NumberScan`) pins every row above, the marker-needs-a-reason rule and the
tolerance of truncated input.
