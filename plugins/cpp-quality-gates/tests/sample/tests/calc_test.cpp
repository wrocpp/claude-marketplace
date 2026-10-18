#include <cstdio>
#include <cstdlib>

#include "calc.hpp"

namespace {
int failures = 0;

void expect(bool ok, const char* what) {
  if (!ok) {
    std::fprintf(stderr, "FAIL %s\n", what);
    ++failures;
  }
}
}  // namespace

int main() {
  expect(clamp_add(1, 2, 0, 10) == 3, "in range");
  expect(clamp_add(-5, 1, 0, 10) == 0, "below");
  expect(clamp_add(9, 9, 0, 10) == 10, "above");

  const char* names[] = {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday", "Someday"};
  for (int day = 0; day < 8; ++day) expect(weekday(day) == names[day], "weekday");
  expect(weekday(99) == "?", "weekday default");

  expect(classify(80, false, 0) == 4, "classify plain");
  return failures == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
