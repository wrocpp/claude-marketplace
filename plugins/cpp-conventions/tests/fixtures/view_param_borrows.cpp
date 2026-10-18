#include <span>
#include <string>
#include <string_view>

int length_of(std::string_view text) { return static_cast<int>(text.size()); }
int total_of(std::span<const int> values) {
    int total = 0;
    for (int v : values) total += v;
    return total;
}

int run() {
    std::string owner = "owned here, borrowed by the call";
    const int numbers[] = {1, 2, 3};
    return length_of(owner) + total_of(numbers);
}
