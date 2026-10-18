export module lib;
import std;

export namespace lib {

struct summary {
  std::string plan;
  std::vector<int> quotas;
};

constexpr std::optional<summary> parse(std::string_view text) {
  if (text.empty()) {
    return std::nullopt;
  }
  summary found{.plan = std::string{text}, .quotas = {}};
  found.quotas.push_back(static_cast<int>(text.size()));
  return found;
}

}  // namespace lib

static_assert(lib::parse("pro")->quotas.front() == 3 && (*lib::parse("pro")).plan == "pro");
