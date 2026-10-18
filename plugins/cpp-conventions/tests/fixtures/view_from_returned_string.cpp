#include <string>
#include <string_view>

std::string make_name();
int use(std::string_view);

int run() {
    std::string_view name = make_name();
    return use(name);
}
