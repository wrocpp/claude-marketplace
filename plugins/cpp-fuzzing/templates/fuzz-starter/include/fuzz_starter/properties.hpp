#pragma once

#include <fuzz_starter/list.hpp>

#include <algorithm>
#include <cstdint>
#include <string_view>

// One property per module, a pure constexpr function of the input text. The fuzz harness, the
// compile-time corpus replay, the bounded-exhaustive check and the unit tests all call these.
namespace fuzz_starter::properties {

// Whatever the text, parsing must not misbehave, and an accepted list survives a format and parse.
constexpr bool parse_holds(std::string_view const text) {
    auto const first = parse_list(text);
    if (!first) {
        return true;
    }
    auto const wire = format_list(*first);
    auto const second = parse_list(std::string_view{wire.data(), wire.size()});
    return second && *second == *first;
}

// For an accepted list the summary agrees with a direct recomputation.
constexpr bool summary_holds(std::string_view const text) {
    auto const items = parse_list(text);
    if (!items) {
        return true;
    }
    std::span<std::int32_t const> const view{*items};
    auto const got = summarise(view);
    std::int64_t sum = 0;
    std::uint32_t mask = 0;
    for (std::size_t index = 0; index < view.size(); ++index) {
        sum += view[index];
        if (view[index] < 0 && index < mask_width) {
            mask |= std::uint32_t{1} << index;
        }
    }
    bool const largest_ok = view.empty() ? got.largest == 0 : std::ranges::all_of(view, [&](auto const item) { return item <= got.largest; });
    bool const mean_ok = view.empty() ? got.mean == 0 : got.mean == sum / static_cast<std::int64_t>(view.size());
    return got.sum == sum && got.negative_mask == mask && largest_ok && mean_ok;
}

}  // namespace fuzz_starter::properties
