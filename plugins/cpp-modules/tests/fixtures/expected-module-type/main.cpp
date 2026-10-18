import lib;
import std;

int main() {
  auto const parsed = lib::parse("pro");
  return parsed && parsed->quotas.size() == 1 && (*parsed).plan == "pro" ? 0 : 1;
}
