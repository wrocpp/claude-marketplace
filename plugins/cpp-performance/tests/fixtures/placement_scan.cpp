// The code-placement experiment: one four-instruction scan loop, compiled twice. The source is the same;
// only the assembler flag differs, and on x86_64 that flag can move the loop's compare-and-jump away from a
// 32-byte boundary. Build and read it with tests/check_placement.py; time it with scripts/alternate.py.
//
//   g++ -std=c++20 -O2 -fno-tree-vectorize -fno-unroll-loops placement_scan.cpp -o scan_plain
//   g++ ... -Wa,-mbranches-within-32B-boundaries placement_scan.cpp -o scan_padded
//   scan_plain plain; scan_padded padded      -> placement,<variant>,<keys>,<ns per scan>
//
// The function can be moved by whole bytes without touching its code: compile to assembly once with
// -fno-toplevel-reorder -falign-functions=1 -falign-loops=1, then assemble that file with -Wa,--defsym,PAD=<n>.
// tests/check_placement.py does that for n = 0 .. 31 and checks where the fused compare-and-jump pairs sit.
//
// On any other CPU the program prints SKIP and exits 0: the flag is x86-only and so is the effect.
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <numeric>
#include <vector>

namespace {
constexpr std::size_t kKeys = 4096;
constexpr int kRepeats = 20000;
constexpr double kNanosecondsPerSecond = 1e9;
}  // namespace

#if defined(__x86_64__)
// PAD bytes of no-ops before the function; a gas symbol, so the compiler output is the same for every PAD.
__asm__(".ifndef PAD\n.set PAD, 0\n.endif\n.text\n.skip PAD, 0x90");
#endif

// The scan under test. noinline keeps it a function of its own so its disassembly can be found by name.
extern "C" __attribute__((noinline)) std::ptrdiff_t scan_for_key(const std::uint32_t* keys, std::size_t count, std::uint32_t wanted) {
  for (std::size_t i = 0; i < count; ++i) {
    if (keys[i] == wanted) return static_cast<std::ptrdiff_t>(i);
  }
  return -1;
}

int main(int argc, char** argv) {
#if defined(__x86_64__)
  const char* variant = argc > 1 ? argv[1] : "unnamed";
  std::vector<std::uint32_t> keys(kKeys);
  std::iota(keys.begin(), keys.end(), std::uint32_t{});
  std::ptrdiff_t sink = 0;
  const auto start = std::chrono::steady_clock::now();
  for (int r = 0; r < kRepeats; ++r) sink += scan_for_key(keys.data(), keys.size(), static_cast<std::uint32_t>(kKeys - 1));
  const double seconds = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
  std::printf("placement,%s,%zu,%.1f\n", variant, kKeys, seconds * kNanosecondsPerSecond / kRepeats);
  return sink < 0;
#else
  (void)argc;
  (void)argv;
  std::puts("SKIP: the placement experiment runs on x86_64 only");
  return 0;
#endif
}
