#include <meta>
#include <string_view>
struct key { std::string_view text; };
struct S { [[=key{"wire"}]] int a; };
constexpr auto m = std::meta::nonstatic_data_members_of(^^S, std::meta::access_context::current())[0];
constexpr auto a = std::meta::annotations_of_with_type(m, ^^key)[0];
int main() {}
