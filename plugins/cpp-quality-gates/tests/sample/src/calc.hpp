#pragma once
#include <string_view>

int clamp_add(int a, int b, int lo, int hi);
std::string_view weekday(int day);
int classify(int score, bool strict, int bonus);
