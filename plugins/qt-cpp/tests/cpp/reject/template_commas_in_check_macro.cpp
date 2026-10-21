// expect-error: macro .CHECK. passed 2 arguments, but takes just 1
// A macro argument is split at every comma outside parentheses, so a template-id with two arguments is two macro
// arguments. accept/check_macro_parens.cpp is the same call with one more pair of parentheses.
#include "../check.hpp"

#include <map>

template <class T>
bool stress(const char*) {
  return true;
}

void run() { CHECK(stress<std::map<int, int>>("x")); }
