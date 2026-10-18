#include <utility>

int main() {
  auto [first, second] = std::pair{1, 2};
  return first + second - 3;
}
