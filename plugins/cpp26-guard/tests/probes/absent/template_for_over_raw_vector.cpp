#include <meta>
enum class E { a, b };
int count() {
  int n = 0;
  template for (constexpr auto e : std::meta::enumerators_of(^^E)) { (void)e; ++n; }
  return n;
}
int main() {}
