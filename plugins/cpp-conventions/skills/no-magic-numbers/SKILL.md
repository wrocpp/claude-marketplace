---
name: no-magic-numbers
description: Use BEFORE writing or reviewing code that contains numbers - limits, timeouts, sizes, thresholds, retry counts, ports, array sizes, test tolerances, CSS lengths and colours. Name every number once, where it comes from (a requirement, a standard's criterion, a measurement), and reference the name; only 0, 1 and 100% stand bare. Covers where a constant lives, how to cite its source, the guard test that keeps it that way, and the advisory pre-write scanner with its exact exemptions. Triggers - magic number, hard-coded, constexpr, limit, threshold, retries, buffer size, tolerance, named constant, magic-ok.
---

# Name every number once

A bare `4096` tells the reader nothing and invites a second `4096` that drifts. Give each number a name at the
one place it is defined, say **where it comes from**, and use the name everywhere.

```cpp
// limits.hpp
inline constexpr std::size_t kFrameHeaderBytes = 8;                   // REQ-NET-012, header layout
inline constexpr std::size_t kMaxPayloadBytes = 4096;                 // RFC 1234 section 3.2, maximum segment
inline constexpr std::size_t kMaxFrameBytes = kFrameHeaderBytes + kMaxPayloadBytes;
inline constexpr auto kRetryBackoff = 250ms;                          // measured p99 of the upstream, 2026-09

static_assert(kMaxFrameBytes <= 65535, "frame must fit the 16-bit length field");   // guard
```

## Rules

1. **Only `0`, `1` and `100%` stand bare** (in any spelling: `0u`, `1.0f`, `-1`, `1s`; `100` where the line says
   percent). Everything else is named: sizes, timeouts, retry counts, ports, exit codes, array sizes, bit
   widths, tolerances, magic strings of digits.
2. **The name says what it is, the line beside it says where it comes from**: a requirement ID, a standard's clause
   or criterion, a measurement with its date. If the source is only "somebody's guess", write that; it is still better
   than silence because it can be found and revisited.
3. **Define once, in one place** (a constants header or module per layer). A second definition of the same
   value is a bug; derive related values from the first (`kMaxFrameBytes` above).
4. **Array sizes come from named constants** (`std::array<char, kMaxFrameBytes>`), not literals.
5. **Test thresholds come from the same constants module as the code.** A test that asserts `== 4096` instead
   of `== kMaxPayloadBytes` passes after someone changes the limit. The scanner exempts literals inside assertion
   macros in test files only because it cannot tell an expected value from a threshold; do not take that as
   permission for thresholds. Tolerances (`EXPECT_NEAR(x, y, 1e-6)`) are named too.
6. **Other languages follow the same rule.** CSS values live as tokens in `:root`; a colour is a number.
7. **Back it with a guard test** (below), or the rule decays.

## Guard test

Fail the build when a bare number appears in the source tree:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/number_scan.py" --check src/ include/
```

Run it from CTest or CI next to the unit tests. Put the numbers the project accepts as bare in
`.claude/cpp-conventions.json` (`{"numbers": {"allow": [2, 8]}}`), and mark a deliberate literal with
`// magic-ok: <where the number comes from>` (a reason is required).

Relations between constants belong in `static_assert`s beside them (as above): the compiler then guards
the relation itself.

## Pre-write scan

`hooks/pre_write_scan.py` scans the C++ text of each write and reports bare numbers to Claude before the file
changes. Advisory by default. `{"numbers": {"block": true}}` in `.claude/cpp-conventions.json` makes it block
(exit 2); `{"numbers": {"disable": true}}` turns it off.

Exactly what is exempt, and what the scanner misses: `references/scanner.md`.

## Checklist

- [ ] Every number except 0, 1 and 100% has a name, defined once, with its source beside it.
- [ ] Array sizes and test thresholds use the named constants.
- [ ] Related constants are derived, and a `static_assert` states the relation.
- [ ] The guard test passes on the files you touched.
