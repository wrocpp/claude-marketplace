// The correctness gate: the same seeded random driver for every implementation that will be timed.
//
//   g++ -std=c++20 -DIMPL_HEADER='"fenwick_correct.hpp"' gate_driver.cpp -o gate && ./gate        exit 0, "gate,PASS,..."
//   g++ -std=c++20 -DIMPL_HEADER='"fenwick_wrong.hpp"'   gate_driver.cpp -o gate && ./gate        exit 1, "gate,FAIL,..."
//   ./gate smoke    a handful of fixed calls: the wrong copy passes these, which is why the random driver exists
//
// The reference is a plain vector summed by hand. Nothing here is timed.
#include IMPL_HEADER

#include <cstdio>
#include <cstring>
#include <random>
#include <vector>

namespace {
constexpr unsigned kFirstSeed = 1;
constexpr unsigned kSeeds = 8;
constexpr int kStepsPerSeed = 2000;
constexpr std::size_t kLargestSize = 64;
constexpr int kLargestDelta = 9;
constexpr int kSmokeSize = 5;  // the smoke test touches positions 0 .. 2 only, never the last slot
constexpr long kSmokeFirst = 1;
constexpr long kSmokeSecond = 4;

struct Mismatch {
  unsigned seed;
  int step;
  std::size_t index;
  long expected;
  long actual;
};

long sum_to(const std::vector<long>& values, std::size_t index) {
  long sum = 0;
  for (std::size_t i = 0; i <= index; ++i) sum += values[i];
  return sum;
}

bool check_all(const Fenwick& tree, const std::vector<long>& reference, unsigned seed, int step, Mismatch& found) {
  for (std::size_t i = 0; i < reference.size(); ++i) {
    const long expected = sum_to(reference, i);
    const long actual = tree.prefix(i);
    if (expected != actual) {
      found = {seed, step, i, expected, actual};
      return false;
    }
  }
  return true;
}

bool run_seed(unsigned seed, Mismatch& found) {
  std::mt19937 rng(seed);
  const std::size_t size = std::uniform_int_distribution<std::size_t>(1, kLargestSize)(rng);
  Fenwick tree(size);
  std::vector<long> reference(size, 0);
  std::uniform_int_distribution<std::size_t> position(0, size - 1);
  std::uniform_int_distribution<int> delta(-kLargestDelta, kLargestDelta);
  for (int step = 0; step < kStepsPerSeed; ++step) {
    const std::size_t at = position(rng);
    const int change = delta(rng);
    tree.add(at, change);
    reference[at] += change;
    if (!check_all(tree, reference, seed, step, found)) return false;
  }
  return true;
}

bool smoke() {
  Fenwick tree(kSmokeSize);
  tree.add(0, kSmokeFirst);
  tree.add(2, kSmokeSecond);
  return tree.prefix(0) == kSmokeFirst && tree.prefix(1) == kSmokeFirst && tree.prefix(2) == kSmokeFirst + kSmokeSecond;
}
}  // namespace

int main(int argc, char** argv) {
  if (argc > 1 && std::strcmp(argv[1], "smoke") == 0) {
    std::printf("smoke,%s\n", smoke() ? "PASS" : "FAIL");
    return smoke() ? 0 : 1;
  }
  Mismatch found{};
  for (unsigned seed = kFirstSeed; seed < kFirstSeed + kSeeds; ++seed) {
    if (!run_seed(seed, found)) {
      std::printf("gate,FAIL,seed %u step %d prefix(%zu) expected %ld got %ld\n", found.seed, found.step, found.index, found.expected, found.actual);
      return 1;
    }
  }
  std::printf("gate,PASS,%u seeds x %d steps\n", kSeeds, kStepsPerSeed);
  return 0;
}
