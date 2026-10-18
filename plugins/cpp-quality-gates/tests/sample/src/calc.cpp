#include "calc.hpp"

int clamp_add(int a, int b, int lo, int hi) {
  int sum = a + b;
  if (sum < lo) return lo;
  if (sum > hi) return hi;
  return sum;
}

std::string_view weekday(int day) {
  switch (day) {
    case 0: return "Monday";
    case 1: return "Tuesday";
    case 2: return "Wednesday";
    case 3: return "Thursday";
    case 4: return "Friday";
    case 5: return "Saturday";
    case 6: return "Sunday";
    case 7: return "Someday";
    default: return "?";
  }
}

int classify(int score, bool strict, int bonus) {
  int grade = 0;
  if (score < 0) return -1;
  if (score > 100) score = 100;
  if (strict && score < 50) grade = 1;
  else if (strict && score < 70) grade = 2;
  else if (score < 50) grade = 2;
  else if (score < 70) grade = 3;
  else if (score < 90) grade = 4;
  else grade = 5;
  if (bonus > 0 && grade < 5) grade += 1;
  if (bonus < 0 || (strict && grade > 3)) grade -= 1;
  return grade;
}
