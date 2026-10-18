#pragma once

#include <cstddef>
#include <span>
#include <string_view>
#include <vector>

namespace fuzz_starter {

// Calls property on every sequence of digits below alphabet, of every length up to longest.
template <class Property>
constexpr bool for_all_sequences(std::size_t const alphabet, std::size_t const longest, Property&& property) {
    std::vector<std::size_t> digits;
    for (std::size_t length = 0; length <= longest; ++length) {
        digits.assign(length, 0);
        for (;;) {
            if (!property(std::span<std::size_t const>{digits})) {
                return false;
            }
            std::size_t place = 0;
            while (place < length && ++digits[place] == alphabet) {
                digits[place++] = 0;
            }
            if (place == length) {
                break;
            }
        }
    }
    return true;
}

// The text lives in a buffer of exactly its size, not in a std::string: a std::string keeps a
// terminator after the last character, so reading one past the end would go unnoticed.
constexpr bool for_all_texts(std::string_view const alphabet, std::size_t const longest, bool (*property)(std::string_view)) {
    return for_all_sequences(alphabet.size(), longest, [&](std::span<std::size_t const> const digits) {
        std::vector<char> text;
        text.reserve(digits.size());
        for (auto const digit : digits) {
            text.push_back(alphabet[digit]);
        }
        text.shrink_to_fit();
        return property(std::string_view{text.data(), text.size()});
    });
}

}  // namespace fuzz_starter
