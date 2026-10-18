#include <chrono>

using WallClock = std::chrono::system_clock;
using Timestamp = std::chrono::time_point<WallClock, std::chrono::milliseconds>;

struct Session {
    Timestamp opened;
    std::chrono::seconds ttl;
};

constexpr bool expired(const Session& session, Timestamp now) { return now >= session.opened + session.ttl; }

static_assert(expired({.opened = Timestamp{std::chrono::milliseconds{1000}}, .ttl = std::chrono::seconds{1}}, Timestamp{std::chrono::milliseconds{2000}}));

int main() { return 0; }
