#include <string>
#include <utility>

std::string make() {
    std::string out = "a value long enough to leave the small-string buffer";
    return std::move(out);
}
