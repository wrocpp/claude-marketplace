// expect-error: One Definition Rule|violates the C\+\+ One Definition Rule
// Two translation units that define a class of the same name differently. Linked with -flto -Wodr -Werror the
// linker reports it; without them the program links and the second definition silently wins. This is the build a
// test of a class-template specialization shared by two files must use (odr_consistent is the control that links).
struct Row {
  int value;
  int Read() const { return value; }
};

int read_in_a(const Row& row) { return row.Read(); }
Row make_in_a() { return Row{1}; }
int main() { return read_in_a(make_in_a()) - 1; }
