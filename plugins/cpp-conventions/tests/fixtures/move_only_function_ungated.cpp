#include <functional>

int main() {
    std::move_only_function<int()> callback{[] { return 0; }};
    return callback();
}
