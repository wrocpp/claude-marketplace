import std;

enum class level { debug, info, warning };

constexpr std::string_view name_of(level v) {
    switch (v) {
        case level::debug: return "debug";
        case level::info: return "info";
        case level::warning: return "warning";
    }
    return {};
}

constexpr auto table = std::to_array<std::pair<std::string_view, level>>({
    {"debug", level::debug},
    {"info", level::info},
    {"warning", level::warning},
});

void parse(std::string_view w) {
    if (w == "--json") {}
    else if (w == "--dry-run") {}
    else if (w == "--verbose") {}
    else if (w == "--quiet") {}
}

struct usage { int input; int output; int cache; };

auto to_pairs(usage const& s) {
    return make({
        {"input", number(s.input)},
        {"output", number(s.output)},
        {"cache", number(s.cache)},
    });
}

auto next(int bits) { return static_cast<level>(bits % 3); }
