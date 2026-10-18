#include <concepts>

template <std::integral T>
constexpr T twice(T value) { return value * 2; }

static_assert(twice(21) == 42);
int main() {}
