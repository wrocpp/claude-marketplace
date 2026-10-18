# Which undefined behaviour each check caught

Fixture: `templates/fuzz-starter`, defect chosen with `-DFUZZ_STARTER_PLANTED_BUG=<name>`;
`tests/run.sh` asserts every row marked "build" on each run.

Measured with GCC 16.2.0 (Homebrew, macOS arm64; Docker `gcc:16`, Debian 13, aarch64) and
Homebrew Clang 23.1.1 for the compile-time columns. Run-time sanitizers: GCC's ASan and UBSan.
The unit test (`tests/unit_test.cpp`, hand-picked cases) passed for every defect.

| Planted defect | Class | Unit test | Compile time: targets that failed | GCC 16.2 diagnostic | ASan/UBSan on corpus replay |
|---|---|---|---|---|---|
| `overflow` | signed overflow in `value * 10 - digit`, guard removed | pass | corpus only (needs 10 digits) | `overflow in constant expression` | UBSan: signed integer overflow |
| `oob` | read at `text[size]`, bound check after the read | pass | corpus and exhaustive, both properties | `non-constant condition for static assertion` (libstdc++ bounds assert on `string_view::operator[]`) | ASan: heap-buffer-overflow |
| `uninit` | `std::size_t digits;` never set | pass | corpus and exhaustive, both | `the value of 'digits' is not usable in a constant expression` | nothing reported (needs MSan or Valgrind; not run) |
| `null` | `*find_largest(items)` on an empty list | pass | `summary` corpus and exhaustive | `dereferencing a null pointer` | UBSan: load of null pointer |
| `divzero` | `sum / items.size()` on an empty list | pass | `summary` corpus and exhaustive | `'(0 / 0)' is not a constant expression` | UBSan: division by zero |
| `shift` | `1u << index` with index of 32 or more | pass | `summary` corpus only (needs 33 items) | `right operand of shift expression '(1 << 32)' is greater than or equal to the precision` | UBSan: shift exponent 32 is too large |
| `roundtrip` | formatter drops the sign of -1 to -9 (logic, not UB) | pass | `parse` corpus and exhaustive | `static assertion failed: <your message>` | the harness aborts: `property failed` |
| `runtime_only` | over-read on the `if !consteval` fast path | pass | none: the build succeeds | n/a | ASan: heap-buffer-overflow |

Clang 23.1.1 failed the same target sets for every row (run by hand; `tests/run.sh` runs only the
correct code with Clang, and only when `CLANGXX` is set); its notes read `dereferencing a null pointer is not
allowed in a constant expression`, `division by zero`, `shift count 32 >= width of type`,
`read of dereferenced one-past-the-end pointer is not allowed`, `increment of uninitialized object`,
and `value -9999999990 is outside the range of representable values of type 'int'`.

## Reading the table

- Constant evaluation caught every UB class in the fixture that an input reached, with the exact
  expression named. It cannot catch what the checked inputs do not reach: `overflow` and `shift`
  need inputs longer than the exhaustive bound, so only the seed corpus (`too_big`, `forty`) fails.
  Put the long seed in the corpus, or raise the bound.
- Only a sanitizer on a real run saw `runtime_only`; only an uninitialised-memory tool (MSan,
  Valgrind) would see `uninit` at run time, and the unit test ran it without complaint because the
  stack slot happened to be zero.
- The correct code passes every row, so a red build is the defect and not the check.

## One-past-the-end reads and std::string

A `std::string` keeps a terminator after its last character. Reading `str.data()[str.size()]` is
legal, returns `'\0'`, and a compile-time check built on `std::string` accepts it (GCC 16.2 and Clang
23.1.1 both accepted it in a one-off fixture). `string_view::operator[]` in libstdc++ 16 has its own
bound check that fires during constant evaluation, which is what `oob` hit. For raw pointer code,
build exhaustive and corpus texts in a `std::vector<char>` of exactly the text's size, as
`include/fuzz_starter/exhaustive.hpp` and `embedded.hpp` do: then `data()[size()]` is
`array subscript value '3' is outside the bounds of array 'heap ' of type 'char [3]'`.
