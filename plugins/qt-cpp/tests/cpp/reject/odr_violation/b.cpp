struct Row {
  long value;  // another type, and another size
  long other;
  int Read() const { return static_cast<int>(value + other); }
};

int read_in_b(const Row& row) { return row.Read(); }
