import std;

enum class level { ok, warning };

consteval char const* name_of(level value) {
  for (auto const enumerator : std::meta::enumerators_of(^^level)) {
    if (std::meta::extract<level>(enumerator) == value) {
      return std::define_static_string(std::meta::identifier_of(enumerator));
    }
  }
  return "";
}

constexpr std::string label() {
  return std::string{name_of(level::ok)};
}

static_assert(label() == "ok");

int main() {}
