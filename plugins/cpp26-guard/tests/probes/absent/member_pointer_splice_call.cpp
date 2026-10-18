#include <meta>
struct S {
  int hits = 0;
  void on() { hits += 1; }
  void run() { template for (constexpr auto m : std::define_static_array(std::meta::members_of(^^S, std::meta::access_context::current()))) if constexpr (std::meta::identifier_of(m) == "on") (this->*[:m:])(); }
};
int main() {}
