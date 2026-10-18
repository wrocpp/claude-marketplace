#include <version>

#if defined(__cpp_lib_move_only_function)
#include <functional>
using Callback = std::move_only_function<void()>;
#elif defined(__cpp_lib_function_ref)
#include <functional>
using Callback = std::function_ref<void()>;
#else
#include <functional>
using Callback = std::function<void()>;
#endif

int main() {
    Callback callback{[] {}};
    callback();
    return 0;
}
