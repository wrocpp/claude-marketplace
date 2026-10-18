export module checked;

export inline int halve(int value) pre(value % 2 == 0) {
  return value / 2;
}
