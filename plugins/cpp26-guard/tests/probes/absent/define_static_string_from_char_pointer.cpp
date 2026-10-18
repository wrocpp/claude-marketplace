#include <meta>
consteval const char* f(const char* s) { return std::define_static_string(s); }
constexpr const char* p = f("hello");
int main() {}
