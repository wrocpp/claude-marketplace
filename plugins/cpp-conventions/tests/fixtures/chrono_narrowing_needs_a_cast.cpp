#include <chrono>

using namespace std::chrono_literals;

constexpr std::chrono::seconds whole = 1500ms;

int main() { return static_cast<int>(whole.count()); }
