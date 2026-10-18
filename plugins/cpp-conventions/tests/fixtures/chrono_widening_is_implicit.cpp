#include <chrono>

using namespace std::chrono_literals;

constexpr std::chrono::milliseconds total = 1s + 250ms;

static_assert(total.count() == 1250);

int main() { return 0; }
