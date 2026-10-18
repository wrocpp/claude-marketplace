#include <memory>
#include <string>

struct Config {
    std::string name;
};

std::shared_ptr<const Config> publish(std::string name) {
    return std::make_shared<const Config>(Config{.name = std::move(name)});
}

int main() { return publish("x")->name.size() == 1 ? 0 : 1; }
