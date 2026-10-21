// expect-error: the value type must be nothrow move constructible and assignable
// A value type whose move can throw is refused at compile time: a throw between the "about" and the "done" signal
// would leave every model mid-change, and a Qt container cannot be prepared before the announcement.
#include "../observable_list.hpp"

struct ThrowingMove {
  ThrowingMove() = default;
  ThrowingMove(const ThrowingMove&) = default;
  ThrowingMove(ThrowingMove&&) noexcept(false) {}
  ThrowingMove& operator=(const ThrowingMove&) = default;
  ThrowingMove& operator=(ThrowingMove&&) noexcept(false) { return *this; }
};

qt_cpp_test::ObservableList<ThrowingMove> refused;
