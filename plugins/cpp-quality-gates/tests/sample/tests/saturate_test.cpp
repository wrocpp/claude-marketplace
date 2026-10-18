#include <climits>
#include <cstdio>
#include <cstdlib>

#include "saturate.hpp"

namespace {
int failures = 0;

void expect(int got, int want, const char* what) {
  if (got != want) {
    std::fprintf(stderr, "FAIL %s: got %d, want %d\n", what, got, want);
    ++failures;
  }
}
}  // namespace

int main() {
  expect(saturating_add(1, 2, 0, 10), 3, "in range");
  expect(saturating_add(-5, 1, 0, 10), 0, "below the lower bound");
  expect(saturating_add(9, 9, 0, 10), 10, "above the upper bound");
  expect(saturating_add(INT_MAX, INT_MAX, INT_MIN, INT_MAX), INT_MAX, "sum wider than int");
  expect(saturating_add(INT_MIN, INT_MIN, INT_MIN, INT_MAX), INT_MIN, "negative sum wider than int");
  expect(saturating_add(4, 6, 0, 10), 10, "exactly on the upper bound");
  expect(saturating_add(-4, 4, 0, 10), 0, "exactly on the lower bound");
  expect(saturating_add(7, 0, 7, 7), 7, "degenerate range");
  return failures == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
