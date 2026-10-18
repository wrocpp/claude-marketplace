---
name: units
description: Use BEFORE writing C++ that handles a duration, a data size, a count of something, a percentage, a rate or a timestamp, and ALWAYS before introducing a new unit or quantity of your own. Quantities carry their unit in the type (std::chrono for time, mp-units for the rest) instead of a bare int whose unit is in its name. Covers the one wall clock, where bare integers still belong, and how to define a unit or a dimension mp-units does not have. Triggers - timeout, _ms, bytes, percent, tokens per second, new unit, custom dimension, timestamp, now(), mp-units, std::chrono.
---

# Quantities carry their unit in the type

`int timeout_ms` compiles the same as `int timeout_s`, and `timeout_ms + grace_s` is accepted
(`bare_integers_mix_units.cpp`). A type makes that mistake a compile error:

| quantity | type |
|---|---|
| duration | `std::chrono::duration` (`std::chrono::milliseconds`, ...) |
| instant | `std::chrono::time_point<Clock, Duration>` |
| size, count with a unit, rate, percentage, frequency | an **mp-units** `quantity` |

Time stays in `std::chrono` even where mp-units is available: it is in the standard, and the rest of the world's
APIs take it. Convert at the boundary if you use both.

## Rules

1. **No bare integer or double with the unit in its name** (`_ms`, `_bytes`, `_pct`) in an interface. Take and
   return the quantity type; unwrap only at a boundary that needs a number (a socket option, a wire field, a log line).
2. **One wall clock.** Pick one alias, e.g. `using WallClock = std::chrono::system_clock;
   using Timestamp = std::chrono::time_point<WallClock, std::chrono::milliseconds>;`
   (`wall_clock_single_source.cpp`). Do not read `time()`, `gettimeofday` or `clock_gettime` elsewhere. Code that
   needs "now" takes the instant as a parameter, or a small clock function, so a test can supply it. Time points
   of different clocks do not subtract (`chrono_mixed_clocks_do_not_subtract.cpp`); that error is the point. Measure
   intervals with `steady_clock`, and convert to `WallClock` only to display or store an instant.
3. **Widening is implicit, narrowing is explicit.** `1s + 250ms` is `milliseconds`
   (`chrono_widening_is_implicit.cpp`); `seconds s = 1500ms;` does not compile
   (`chrono_narrowing_needs_a_cast.cpp`): write `duration_cast` (truncates) or `round`/`floor`/`ceil`, and say which.
4. **Name the number once** (see `no-magic-numbers`): `constexpr auto kTimeout = 30s;`, not `30` in a call.
5. **Where bare integers still belong:** array and container indices, element counts that are plain counts, loop
   counters, enum values, bit masks, protocol fields and syscall arguments at the single place that converts. Even
   there, a count of "tokens" or "bytes" that crosses a function boundary should be a quantity.

## Defining a unit or dimension that does not exist

Do not use a bare integer because the library lacks the unit. In mp-units a new dimension, quantity kind and
unit are four lines; a derived unit is a magnitude times another unit. Worked example, compiled by the tests when
mp-units is available: `references/mp-units.md`.

## Evidence

`tests/fixtures/chrono_*.cpp` (all compilers agree) and `tests/optional/mp_units_*.cpp` (run when mp-units is
found, with `MP_UNITS_DIR=<checkout>` or `WROCPP_NETWORK=1`). Results: `references/mp-units.md`.
