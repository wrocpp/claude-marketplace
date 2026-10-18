#include <thread>

int shared;

int main() {
  std::thread first([] { for (int i = 0; i < 1000; ++i) ++shared; });
  std::thread second([] { for (int i = 0; i < 1000; ++i) ++shared; });
  first.join();
  second.join();
  return shared == 0;
}
