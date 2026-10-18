#include <chrono>

auto elapsed(std::chrono::system_clock::time_point wall, std::chrono::steady_clock::time_point mono) {
    return wall - mono;
}
