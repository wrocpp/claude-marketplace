#pragma once

#include <cstddef>
#include <cstdint>
#include <limits>
#include <optional>
#include <span>
#include <string_view>
#include <utility>
#include <vector>

// FUZZ_STARTER_BUG selects one planted defect; 0 is the correct code. The numbers are the
// values of the FUZZ_STARTER_PLANTED_BUG CMake option (see cmake/FuzzStarter.cmake).
#ifndef FUZZ_STARTER_BUG
#define FUZZ_STARTER_BUG 0
#endif

namespace fuzz_starter {

inline constexpr std::size_t mask_width = 32;

constexpr bool is_digit(char const c) { return c >= '0' && c <= '9'; }

// The run-time branch is a pointer-based fast path. Constant evaluation takes the other branch,
// so a defect in this one is invisible to the compile-time checks and only a sanitizer finds it.
constexpr bool digit_at(std::string_view const text, std::size_t const at) {
    if consteval {
#if FUZZ_STARTER_BUG == 2
        return is_digit(text[at]) && at < text.size();
#else
        return at < text.size() && is_digit(text[at]);
#endif
    } else {
        char const* const data = text.data();
#if FUZZ_STARTER_BUG == 2
        return is_digit(data[at]) && at < text.size();
#elif FUZZ_STARTER_BUG == 8
        return at < text.size() + 1 && is_digit(data[at]);
#else
        return at < text.size() && is_digit(data[at]);
#endif
    }
}

// "12,-7,300" -> {12, -7, 300}. Empty text is the empty list; an empty element, a lone sign, a
// trailing comma or a value outside int32 is rejected.
constexpr std::optional<std::vector<std::int32_t>> parse_list(std::string_view const text) {
    constexpr auto lowest = std::numeric_limits<std::int32_t>::min();
    std::vector<std::int32_t> items;
    std::size_t at = 0;
    while (at < text.size()) {
        bool const negative = text[at] == '-';
        at += negative ? 1 : 0;
        std::int32_t value = 0;
#if FUZZ_STARTER_BUG == 3
        std::size_t digits;
#else
        std::size_t digits = 0;
#endif
        for (; digit_at(text, at); ++at, ++digits) {
            std::int32_t const digit = text[at] - '0';
#if FUZZ_STARTER_BUG != 1
            if (value < (lowest + digit) / 10) {
                return std::nullopt;
            }
#endif
            value = value * 10 - digit;
        }
        if (digits == 0) {
            return std::nullopt;
        }
        if (!negative) {
            if (value == lowest) {
                return std::nullopt;
            }
            value = -value;
        }
        items.push_back(value);
        if (at < text.size()) {
            if (text[at] != ',' || at + 1 == text.size()) {
                return std::nullopt;
            }
            ++at;
        }
    }
    return items;
}

constexpr void append_number(std::vector<char>& out, std::int32_t const value) {
#if FUZZ_STARTER_BUG == 7
    bool const negative = value <= -10;
#else
    bool const negative = value < 0;
#endif
    std::uint32_t magnitude = value < 0 ? 0U - static_cast<std::uint32_t>(value) : static_cast<std::uint32_t>(value);
    if (negative) {
        out.push_back('-');
    }
    std::size_t const start = out.size();
    do {
        out.push_back(static_cast<char>('0' + magnitude % 10));
        magnitude /= 10;
    } while (magnitude != 0);
    for (std::size_t low = start, high = out.size() - 1; low < high; ++low, --high) {
        std::swap(out[low], out[high]);
    }
}

constexpr std::vector<char> format_list(std::span<std::int32_t const> const items) {
    std::vector<char> out;
    for (std::size_t index = 0; index < items.size(); ++index) {
        if (index != 0) {
            out.push_back(',');
        }
        append_number(out, items[index]);
    }
    return out;
}

struct summary {
    std::int64_t sum = 0;
    std::int32_t largest = 0;
    std::int64_t mean = 0;
    std::uint32_t negative_mask = 0;
    constexpr bool operator==(summary const&) const = default;
};

constexpr std::int32_t const* find_largest(std::span<std::int32_t const> const items) {
    std::int32_t const* best = nullptr;
    for (auto const& item : items) {
        if (best == nullptr || item > *best) {
            best = &item;
        }
    }
    return best;
}

constexpr summary summarise(std::span<std::int32_t const> const items) {
    summary result;
    for (std::size_t index = 0; index < items.size(); ++index) {
        result.sum += items[index];
#if FUZZ_STARTER_BUG == 6
        if (items[index] < 0) {
            result.negative_mask |= std::uint32_t{1} << index;
        }
#else
        if (items[index] < 0 && index < mask_width) {
            result.negative_mask |= std::uint32_t{1} << index;
        }
#endif
    }
#if FUZZ_STARTER_BUG == 4
    result.largest = *find_largest(items);
#else
    result.largest = items.empty() ? 0 : *find_largest(items);
#endif
#if FUZZ_STARTER_BUG == 5
    result.mean = result.sum / static_cast<std::int64_t>(items.size());
#else
    result.mean = items.empty() ? 0 : result.sum / static_cast<std::int64_t>(items.size());
#endif
    return result;
}

}  // namespace fuzz_starter
