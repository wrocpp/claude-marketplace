// The control for reject/odr_violation: two translation units that agree on the class, linked with the same flags.
#include "row.hpp"
int read_in_a(const Row& row);
Row make_in_b();
int main() { return read_in_a(make_in_b()) - 1; }
