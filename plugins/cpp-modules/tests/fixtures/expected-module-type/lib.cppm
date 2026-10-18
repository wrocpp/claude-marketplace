export module lib;
import std;

export namespace lib {

struct summary {
  std::string plan;
  std::vector<int> quotas;
};

struct failure {
  int offset{};
};

constexpr std::expected<summary, failure> parse(std::string_view text) {
  if (text.empty()) {
    return std::unexpected{failure{0}};
  }
  summary found{.plan = std::string{text}, .quotas = {}};
  found.quotas.push_back(static_cast<int>(text.size()));
  return found;
}

}  // namespace lib

static_assert(lib::parse("pro")->quotas.front() == 3 && (*lib::parse("pro")).plan == "pro");
