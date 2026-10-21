// A minimal check harness: no test framework, assertions that survive NDEBUG.
#pragma once

#include <cstdio>
#include <cstdlib>

namespace qt_cpp_test {

inline int& failures() {
  static int n = 0;
  return n;
}

inline void report(bool ok, char const* expr, char const* file, int line) {
  if (ok) return;
  ++failures();
  std::fprintf(stderr, "%s:%d: CHECK failed: %s\n", file, line, expr);
}

inline int finish(char const* name) {
  std::printf("%s: %s\n", name, failures() == 0 ? "ok" : "FAILED");
  return failures() == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}

}  // namespace qt_cpp_test

// A macro argument is split at every comma outside parentheses, so CHECK(f<QMap<int, S>>()) is two arguments:
// write CHECK((f<QMap<int, S>>())).
#define CHECK(cond) ::qt_cpp_test::report(static_cast<bool>(cond), #cond, __FILE__, __LINE__)
