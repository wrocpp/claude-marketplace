#include <string_view>

#include "../skills/reflect-dont-hand-write/references/reflect.hpp"

enum class level { debug, info, warning, error };
enum class alias { a, b, c = b };

struct options {
    [[= refl::make_flag("--json")]] bool as_json = false;
    [[= refl::make_flag("--dry-run")]] bool dry_run = false;
    int jobs = 1;
};

struct point {
    int x;
    int y;
};

static_assert(refl::enum_count<level> == 4);
static_assert(refl::enum_name(level::warning) == "warning");
static_assert(refl::enum_name(static_cast<level>(99)).empty());
static_assert(refl::enum_from_name<level>("info") == level::info);
static_assert(!refl::enum_from_name<level>("INFO").has_value());
static_assert(refl::enum_values<level>[3] == level::error);
static_assert(refl::unique_values<level>());
static_assert(!refl::unique_values<alias>());

constexpr bool round_trips() {
    for (auto const value : refl::enum_values<level>) {
        if (refl::enum_from_name<level>(refl::enum_name(value)) != value) {
            return false;
        }
    }
    return true;
}
static_assert(round_trips());

constexpr options parsed() {
    options result;
    refl::set_flag(result, "--dry-run");
    return result;
}
static_assert(parsed().dry_run && !parsed().as_json);
constexpr bool unknown_flag_is_refused() {
    options result;
    return !refl::set_flag(result, "--nope");
}
static_assert(unknown_flag_is_refused());

constexpr int sum_of_members() {
    int total = 0;
    refl::for_each_member(point{3, 4}, [&](std::string_view name, int value) { total += name.size() * value; });
    return total;
}
static_assert(sum_of_members() == 7);

int main() {
    options result;
    return refl::set_flag(result, "--json") && result.as_json && !refl::set_flag(result, "--nope") ? 0 : 1;
}
