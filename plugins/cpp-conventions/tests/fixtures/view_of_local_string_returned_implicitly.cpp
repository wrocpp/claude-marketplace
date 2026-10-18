#include <string>
#include <string_view>

std::string_view label() {
    std::string text = "a label long enough to leave the small-string buffer behind";
    return text;
}
