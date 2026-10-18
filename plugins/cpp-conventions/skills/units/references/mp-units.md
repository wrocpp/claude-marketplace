# mp-units notes

Tested against mp-units **v2.5.0** (header-only; `src/core/include` and `src/systems/include`), `-std=c++23`.
Fixtures: `tests/optional/`. They run with `MP_UNITS_DIR=<checkout>` or `WROCPP_NETWORK=1` (clones the pinned tag
into `$WROCPP_CACHE_DIR`); otherwise the runner prints `SKIP mp-units fixtures`.

## Arithmetic and conversion

```cpp
#include <mp-units/systems/si.h>
using namespace mp_units;
using namespace mp_units::si::unit_symbols;

constexpr quantity distance = 120 * km;
constexpr quantity duration = 2 * h;
constexpr quantity speed = distance / duration;          // derived unit, checked
static_assert(speed == 60 * km / h);
static_assert(120 * km + 500 * m == 120500 * m);         // common unit chosen for you
```

- `5 * km + 3 * s` is rejected: dimensions differ (`mp_units_dimension_mismatch.cpp`).
- `constexpr quantity<si::second> timeout = 30;` is rejected: a bare number does not become a quantity
  (`mp_units_bare_number_to_quantity.cpp`). Write `30 * s`.
- Converting to a unit that loses precision needs the representation spelled out:
  `q.in<double>(m / s)`; `q.in(unit)` is for exact conversions.
- `25. * percent` and `.in(one)` give the ratio `0.25`; a count per second is `400 * one / s`
  (`mp_units_rate_and_percent.cpp`).

## Defining a new dimension, quantity and unit

A count the SI does not define - LLM tokens, frames, messages:

```cpp
inline constexpr struct token_dim final : base_dimension<"T"> {} token_dim;
inline constexpr struct token_count final : quantity_spec<token_dim> {} token_count;
inline constexpr struct token final : named_unit<"tok", kind_of<token_count>> {} token;
inline constexpr struct kilotoken final : named_unit<"ktok", mag_power<10, 3> * token> {} kilotoken;

constexpr quantity prompt = 1500 * token;
constexpr quantity window = 8 * kilotoken;
static_assert(prompt < window);
static_assert(window == 8000 * token);
static_assert(prompt.in<double>(kilotoken) == 1.5 * kilotoken);
```

Steps: (1) a `base_dimension` with a short symbol; (2) a `quantity_spec` of that dimension (this is what the type
checker compares); (3) a `named_unit` that is `kind_of` that quantity; (4) multiples as `mag<N> * unit`
or `mag_power<B, E> * unit`. A rate is then `token / s`, a throughput check needs no extra code.

If the quantity already exists in the library (a length, a duration, a frequency), use its unit and derive yours
from it with a magnitude; a new base dimension is for a quantity that has no physical dimension to borrow.

## Measured

**A** accepted, **R** rejected. The reject rows are rejected for the reason described above, not for a missing header.

| fixture | GCC 16.2 | Apple clang 21 | Clang 21 | Clang 22.1.8 | Clang 23 | Clang 19 |
|---|---|---|---|---|---|---|
| `mp_units_quantity_arithmetic` | A | A | A | A | A | not run |
| `mp_units_dimension_mismatch` | R | R | R | R | R | not run |
| `mp_units_bare_number_to_quantity` | R | R | R | R | R | not run |
| `mp_units_define_a_unit` | A | A | A | **R** | A | not run |
| `mp_units_rate_and_percent` | A | A | A | **R** | A | not run |

Clang 22.1.8 rejects `8 * kilotoken` and `25. * percent` against v2.5.0 (the `operator*(M, U)` constraint on a
unit is reported as not satisfied); 21 and 23 accept. Clang 19 cannot parse the headers at all (`type constraint
differs in template redeclaration`), so the runner skips it. Use GCC 14+ or Clang 21/23 with mp-units 2.5.

Cite: the mp-units documentation for `base_dimension`, `quantity_spec` and `named_unit`; for `std::chrono`
use the `cppreference` skill (`topics chrono`).
