#include <cstdlib>

int main() {
  void* volatile block = std::malloc(64);
  block = nullptr;
  return 0;
}
