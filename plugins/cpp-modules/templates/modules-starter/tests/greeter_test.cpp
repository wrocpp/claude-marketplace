import starter.greeter;
import std;

namespace {

int failures = 0;

void expect_equal(std::string_view const actual, std::string_view const expected, std::string_view const what) {
  if (actual != expected) {
    ++failures;
    std::println(std::cerr, "{}: expected \"{}\", got \"{}\"", what, expected, actual);
  }
}

}  // namespace

int main() {
  expect_equal(starter::greet("Wro.cpp"), "Hello, Wro.cpp!", "named greeting");
  expect_equal(starter::greet(""), "Hello, stranger!", "empty name");
  expect_equal(starter::greet(std::string(starter::longest_name + 1, 'x')), "Hello, stranger!", "name over the limit");
  return failures == 0 ? 0 : 1;
}
