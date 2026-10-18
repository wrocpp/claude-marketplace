#include <string>
#include <string_view>

int use(std::string_view);

int run() {
    std::string_view name = std::string("a name too long for the small-string buffer, on purpose");
    return use(name);
}
