int halve(int value) pre(value % 2 == 0) {
  return value / 2;
}

int main() {
  return halve(4) == 2 ? 0 : 1;
}
