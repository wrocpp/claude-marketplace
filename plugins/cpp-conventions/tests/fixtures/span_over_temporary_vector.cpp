#include <span>
#include <vector>

std::vector<int> make_values();
int sum(std::span<const int>);

int run() {
    std::span<const int> values = make_values();
    return sum(values);
}
