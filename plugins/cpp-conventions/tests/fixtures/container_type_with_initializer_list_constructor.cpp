#include <initializer_list>
#include <string>
#include <utility>
#include <vector>

class Headers {
public:
    Headers() = default;
    Headers(std::initializer_list<std::pair<std::string, std::string>> fields) {
        for (const auto& [name, value] : fields) add(name, value);
    }

    void add(std::string name, std::string value) { fields_.emplace_back(std::move(name), std::move(value)); }
    std::size_t size() const { return fields_.size(); }

private:
    std::vector<std::pair<std::string, std::string>> fields_;
};

const Headers headers{{"accept", "text/html"}, {"accept", "application/json"}};
const Headers none;

int main() { return headers.size() == 2 && none.size() == 0 ? 0 : 1; }
