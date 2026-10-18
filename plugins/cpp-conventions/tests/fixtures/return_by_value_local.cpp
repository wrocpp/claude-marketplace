#include <string>
#include <vector>

std::vector<std::string> make() {
    std::vector<std::string> out;
    out.push_back("a");
    return out;
}

int main() { return make().size() == 1 ? 0 : 1; }
