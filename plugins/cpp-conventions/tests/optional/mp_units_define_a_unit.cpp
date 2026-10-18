#include <mp-units/systems/si.h>

using namespace mp_units;

inline constexpr struct token_dim final : base_dimension<"T"> {} token_dim;
inline constexpr struct token_count final : quantity_spec<token_dim> {} token_count;
inline constexpr struct token final : named_unit<"tok", kind_of<token_count>> {} token;
inline constexpr struct kilotoken final : named_unit<"ktok", mag_power<10, 3> * token> {} kilotoken;

constexpr quantity prompt = 1500 * token;
constexpr quantity window = 8 * kilotoken;

static_assert(prompt < window);
static_assert(window == 8000 * token);
static_assert(prompt.in<double>(kilotoken) == 1.5 * kilotoken);

int main() { return 0; }
