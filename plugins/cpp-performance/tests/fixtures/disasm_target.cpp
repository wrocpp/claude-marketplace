// A program with a template function in a namespace, so its symbol is mangled (_ZN12perf_fixture6sum_toIiEET_S1_)
// and only an unmangled search (objdump -C) finds it by the name a person types.
namespace perf_fixture {
template <class T>
__attribute__((noinline)) T sum_to(T n) {
  T total = 0;
  for (T i = 1; i <= n; ++i) total += i;
  return total;
}
}  // namespace perf_fixture

int main(int argc, char**) { return perf_fixture::sum_to<int>(argc) == 1 ? 0 : 1; }
