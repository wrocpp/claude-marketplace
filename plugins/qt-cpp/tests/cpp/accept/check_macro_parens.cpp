// The call that template_commas_in_check_macro.cpp rejects, with one more pair of parentheses around the argument.
#include "../check.hpp"

#include <map>

template <class T>
bool stress(const char*) {
  return true;
}

void run() { CHECK((stress<std::map<int, int>>("x"))); }
