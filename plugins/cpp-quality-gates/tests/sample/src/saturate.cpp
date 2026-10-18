#include "saturate.hpp"

int saturating_add(int a, int b, int lo, int hi) {
  long long sum = static_cast<long long>(a) + b;
  if (sum < lo) return lo;
  if (sum > hi) return hi;
  return static_cast<int>(sum);
}
