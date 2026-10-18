export module starter.greeter;

import std;

export namespace starter {

constexpr std::size_t longest_name = 32;

constexpr bool is_valid_name(std::string_view const name) {
  return !name.empty() && name.size() <= longest_name;
}

static_assert(is_valid_name("Wro.cpp"));
static_assert(!is_valid_name(""));

std::string greet(std::string_view name);

}  // namespace starter
