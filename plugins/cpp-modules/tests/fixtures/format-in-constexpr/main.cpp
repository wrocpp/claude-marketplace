import std;

constexpr std::string label(int value) {
  return std::format("level {}", value);
}

static_assert(label(3) == "level 3");

int main() {}
