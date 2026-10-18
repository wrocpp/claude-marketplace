#pragma once

#include <cstdio>
#include <exception>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <span>
#include <string_view>
#include <vector>

// The same binary is an AFL++ target and a plain replay tool:
//   fuzz_x file-or-dir...   replays each file (this is what ctest and the compile-time corpus see)
//   fuzz_x < input          runs once on stdin
//   afl-fuzz ... -- fuzz_x  built with afl-g++-fast: persistent loop over shared memory
#ifdef __AFL_FUZZ_INIT
#include <unistd.h>
__AFL_FUZZ_INIT();
#endif

namespace fuzz_starter::driver {

using property_fn = bool (*)(std::string_view);

// A failing property aborts, which AFL++ records as a crash and a sanitizer report precedes.
inline void check(property_fn const property, std::string_view const input) {
    if (!property(input)) {
        std::fputs("property failed\n", stderr);
        std::abort();
    }
}

inline std::vector<char> read_all(std::istream& in) {
    return {std::istreambuf_iterator<char>{in}, std::istreambuf_iterator<char>{}};
}

// The vector holds exactly the bytes read, so a sanitizer sees a read past the end.
inline void check_stream(property_fn const property, std::istream& in) {
    auto const bytes = read_all(in);
    check(property, std::string_view{bytes.data(), bytes.size()});
}

#ifdef __AFL_FUZZ_INIT
}  // namespace fuzz_starter::driver

// The AFL++ macros name globals of the runtime, so they must expand at global scope.
inline void fuzz_starter_afl_loop(fuzz_starter::driver::property_fn const property) {
    __AFL_INIT();
    unsigned char* const buffer = __AFL_FUZZ_TESTCASE_BUF;
    while (__AFL_LOOP(10000)) {
        auto const length = static_cast<std::size_t>(__AFL_FUZZ_TESTCASE_LEN);
        // The shared buffer is far larger than the case; an exact-size copy lets ASan see an over-read.
        std::vector<char> const copy(reinterpret_cast<char*>(buffer), reinterpret_cast<char*>(buffer) + length);
        fuzz_starter::driver::check(property, std::string_view{copy.data(), copy.size()});
    }
}

namespace fuzz_starter::driver {
#endif

inline int replay(property_fn const property, std::span<char* const> const paths) {
    std::size_t replayed = 0;
    for (char* const path : paths) {
        std::filesystem::path const given{path};
        std::vector<std::filesystem::path> files;
        if (std::filesystem::is_directory(given)) {
            for (auto const& entry : std::filesystem::directory_iterator{given}) {
                if (entry.is_regular_file()) {
                    files.push_back(entry.path());
                }
            }
        } else {
            files.push_back(given);
        }
        for (auto const& file : files) {
            std::ifstream in{file, std::ios::binary};
            check_stream(property, in);
            ++replayed;
        }
    }
    std::printf("replayed %zu inputs\n", replayed);
    return replayed == 0 ? 1 : 0;
}

inline int run(int const argc, char** const argv, property_fn const property) {
    if (argc >= 2) {
        return replay(property, std::span<char* const>{argv + 1, static_cast<std::size_t>(argc - 1)});
    }
#ifdef __AFL_FUZZ_INIT
    ::fuzz_starter_afl_loop(property);
    return 0;
#else
    check_stream(property, std::cin);
    return 0;
#endif
}

}  // namespace fuzz_starter::driver
