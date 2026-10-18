#include <mp-units/systems/si.h>

using namespace mp_units;
using namespace mp_units::si::unit_symbols;

constexpr quantity distance = 120 * km;
constexpr quantity duration = 2 * h;
constexpr quantity speed = distance / duration;

static_assert(speed == 60 * km / h);
static_assert(speed.in<double>(m / s) > 16 * m / s);
static_assert(120 * km + 500 * m == 120500 * m);

int main() { return 0; }
