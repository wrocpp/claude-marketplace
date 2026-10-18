module starter.greeter;

import std;

namespace starter {

std::string greet(std::string_view const name) {
  return is_valid_name(name) ? std::format("Hello, {}!", name) : std::string{"Hello, stranger!"};
}

}  // namespace starter
