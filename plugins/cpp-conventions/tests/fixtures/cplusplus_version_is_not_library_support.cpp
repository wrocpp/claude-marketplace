#include <version>

#if __cplusplus > 202302L && !defined(__cpp_lib_function_ref)
#error "C++26 mode, but the standard library does not provide std::function_ref"
#endif

int main() { return 0; }
