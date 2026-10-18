#pragma once

#include <cstddef>
#include <string_view>
#include <vector>

namespace fuzz_starter {

// #embed yields bytes; a char array cannot hold a value of 0x80 or more without a narrowing error,
// so the file is embedded as unsigned char and copied into a buffer of exactly its size.
template <auto Property, std::size_t Size>
constexpr bool embedded_holds(unsigned char const (&bytes)[Size]) {
    std::vector<char> const text(bytes, bytes + Size);
    return Property(std::string_view{text.data(), text.size()});
}

}  // namespace fuzz_starter
