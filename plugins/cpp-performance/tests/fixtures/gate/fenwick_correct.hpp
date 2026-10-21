// A Fenwick tree (prefix sums with point updates), the structure a row index uses to turn a key into a row.
// This is the correct one. fenwick_wrong.hpp differs in one expression.
#pragma once
#include <cstddef>
#include <vector>

class Fenwick {
 public:
  explicit Fenwick(std::size_t size) : tree_(size + 1, 0) {}

  void add(std::size_t index, long delta) {
    for (std::size_t slot = index + 1; slot < tree_.size(); slot += slot & (~slot + 1)) tree_[slot] += delta;
  }

  // The sum of the values at positions 0 .. index, inclusive.
  long prefix(std::size_t index) const {
    long sum = 0;
    for (std::size_t slot = index + 1; slot > 0; slot -= slot & (~slot + 1)) sum += tree_[slot];
    return sum;
  }

 private:
  std::vector<long> tree_;
};
