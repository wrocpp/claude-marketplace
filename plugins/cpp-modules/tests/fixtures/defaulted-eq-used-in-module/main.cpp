import lib;

int main() {
  lib::point const a{1, 2};
  lib::point const b{1, 2};
  return a == b ? 0 : 1;
}
