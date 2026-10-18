import lib;
import std;

int main() {
  constexpr std::string_view shown = std::define_static_string(std::meta::display_string_of(^^lib::level));
  std::println("{}", shown);
  return shown == "lib::level@lib" ? 0 : 1;
}
