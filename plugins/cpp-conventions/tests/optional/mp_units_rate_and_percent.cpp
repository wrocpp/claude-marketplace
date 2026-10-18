#include <mp-units/systems/si.h>

using namespace mp_units;
using namespace mp_units::si::unit_symbols;

constexpr quantity rate = 400 * mp_units::one / s;
constexpr quantity fraction = 25. * percent;

static_assert(fraction.in(one) == 0.25 * one);
static_assert(rate * (2 * s) == 800 * one);

int main() { return 0; }
