import std;

int main() {
  std::vector<std::pair<std::string, std::string>> const headers{{"content-type", "application/json"}, {"accept", "*/*"}};
  return headers.size() == 2 ? 0 : 1;
}
