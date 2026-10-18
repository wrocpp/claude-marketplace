module;
#include <cstdio>
#include <meta>
#include <vector>
export module status;
import std;

export enum class level { debug, info, warning, error };

export template <std::invocable<int> F>
constexpr int apply(F fn) { return fn(1); }

export constexpr std::string_view name_of(level value) {
    template for (constexpr auto e : std::define_static_array(std::meta::enumerators_of(^^level))) {
        if (value == [:e:]) {
            return std::meta::identifier_of(e);
        }
    }
    return {};
}

export void fail(char const* what) {
    std::fprintf(stderr, "%s\n", what);
}

constexpr bool known(std::string_view word) {
    return word == "debug" || word == "info";
}

namespace detail {
// Exception: the wire word is "warn", not the enumerator
constexpr std::string_view wire_warning = "warn";
}  // namespace detail
