# Evidence: designated initializers

Fixtures live in `tests/fixtures/`; `tests/fixtures/expectations.json` states what each compiler must do and
`sh tests/run.sh` checks both directions. Flags are `-std=c++23 -Wall -Wextra -O2 -c` unless the row says otherwise.
Outcome: **A** accepted without a diagnostic, **W** accepted with a warning, **R** rejected.

Compilers measured (macOS 27, arm64; Debian in the `gcc:16` image):

| id | compiler |
|----|----------|
| gcc-16 | GCC 16.2.0 (Homebrew; the `gcc:16` image gives the same result) |
| apple-clang-21 | Apple clang 21.0.0 (clang-2100.3.34.2) |
| clang 21 / 22 / 23 | Homebrew clang 21.1.8, 22.1.8, 23.1.1 |
| clang 19 | Debian clang 19.1.7 (in the `gcc:16` image, after `apt-get install clang`) |

Clang 17 and older are not installed here and were not measured.

| fixture (flags changed) | GCC 16 | Apple clang 21 | Clang 19, 21, 22, 23 |
|---|---|---|---|
| `designated_in_declaration_order` | A | A | A |
| `designated_skip_member_with_default` (also with `-Werror`) | A | A | A |
| `designated_out_of_declaration_order` | **R** `designator order ... does not match declaration order` | W `-Wreorder-init-list` | W `-Wreorder-init-list` |
| `designated_out_of_declaration_order` (`-Werror`) | R | R | R |
| `designated_omit_member_without_default` | W `-Wmissing-field-initializers` | **A** (silent) | W `-Wmissing-designated-field-initializers` |
| same, `-Werror` | R | **A** | R |
| same, `-Wall` only (no `-Wextra`) | A | A | A |
| `designated_same_member_twice` | R `designator used multiple times` | W `-Winitializer-overrides` | W `-Winitializer-overrides` |
| `assign_same_member_twice` (the form the rule replaces) | A | A | A |
| `designated_mixed_with_positional` | R | W `-Wc99-designator` | W `-Wc99-designator` |
| `designated_on_type_with_constructor` | R | R | R |
| `designated_in_cxx17` (`-std=c++17 -Wall -Wextra`) | A | A | A |
| same, `-std=c++17 -pedantic-errors` | R | R | R |

Reading the table:

- The omitted-member row is the trap. The same source is a warning on GCC and upstream Clang, an error under
  `-Werror` there, and invisible on Apple clang 21. Build on both before claiming it is clean.
- The C++17 row shows that "it compiled" does not prove the target accepts C++20 syntax: both compilers take
  designated initializers in C++17 mode as an extension and stay silent.
- Out-of-order designators are the one place GCC is stricter than every Clang.

Rule source: cppreference, aggregate initialization, section "Designated initializer" (designators must
appear in the order of the members) - confirm with the `cppreference` skill:
`cppreference.py lookup "designated initializer" --grep "same order"`.
