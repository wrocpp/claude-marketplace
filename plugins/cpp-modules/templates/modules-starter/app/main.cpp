import starter.greeter;
import std;

int main(int argc, char** argv) {
  std::println("{}", starter::greet(argc > 1 ? std::string_view{argv[1]} : std::string_view{}));
}
