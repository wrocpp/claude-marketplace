#include <map>
#include <string>
#include <vector>

const std::vector<int> sizes{4, 8, 15};
const std::map<std::string, int> ports{{"http", 80}, {"https", 443}};

int main() { return static_cast<int>(sizes.size() + ports.size()) == 5 ? 0 : 1; }
