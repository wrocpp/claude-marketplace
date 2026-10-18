#include <vector>
#include <version>

#if defined(__cpp_lib_ranges_to_container)
#include <ranges>
std::vector<int> doubled(const std::vector<int>& input) {
    return input | std::views::transform([](int v) { return v + v; }) | std::ranges::to<std::vector>();
}
#else
std::vector<int> doubled(const std::vector<int>& input) {
    std::vector<int> out{input};
    for (int& v : out) v += v;
    return out;
}
#endif

int main() { return doubled({1, 2}).size() == 2 ? 0 : 1; }
