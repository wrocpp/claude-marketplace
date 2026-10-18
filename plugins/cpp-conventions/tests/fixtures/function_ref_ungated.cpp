#include <functional>

int apply(std::function_ref<int(int)> fn) { return fn(1); }

int main() { return apply([](int v) { return v - 1; }); }
