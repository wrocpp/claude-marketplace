import std;

int main() {
  return std::add_sat(200, 100) == 300 ? 0 : 1;
}
