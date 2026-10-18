#include <string>
#include <vector>

int total(const std::vector<std::string>& names) {
    int n = 0;
    for (const std::string& name : names) n += static_cast<int>(name.size());
    return n;
}
