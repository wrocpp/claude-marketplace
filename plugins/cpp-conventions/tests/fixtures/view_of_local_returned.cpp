#include <string>
#include <string_view>

std::string_view first_word() {
    std::string line = "alpha beta gamma, long enough to leave the small-string buffer";
    return std::string_view{line}.substr(0, 5);
}
