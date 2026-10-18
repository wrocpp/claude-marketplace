#include <cstdlib>

int main(int argc, char**) {
  int* volatile data = static_cast<int*>(std::malloc(4 * sizeof(int)));
  data[0] = 0;
  int value = data[argc + 3];
  std::free(data);
  return value;
}
