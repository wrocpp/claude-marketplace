#include <fuzz_starter/list.hpp>
#include <fuzz_starter/properties.hpp>

#include <cstdio>
#include <cstdlib>
#include <string_view>
#include <vector>

// The ordinary tests: a few hand-picked examples, as most projects have them. They do not know the
// planted defects exist, which is the point of the compile-time checks next to them.
namespace {

int failures = 0;

void expect(bool const ok, char const* const what) {
    if (!ok) {
        std::fprintf(stderr, "FAIL %s\n", what);
        ++failures;
    }
}

}  // namespace

int main() {
    using namespace fuzz_starter;
    auto const three = parse_list("12,-7,300");
    expect(three && *three == std::vector<std::int32_t>{12, -7, 300}, "parses a list");
    expect(!parse_list("1,,2"), "rejects an empty element");
    expect(!parse_list("1,"), "rejects a trailing comma");
    expect(!parse_list("-"), "rejects a lone sign");
    expect(!parse_list("2147483648"), "rejects a value above int32");
    expect(parse_list("-2147483648").has_value(), "accepts the lowest int32");
    expect(properties::parse_holds("12,300"), "parse property on an example");
    expect(properties::summary_holds("12,-7,300"), "summary property on an example");
    auto const list = summarise(std::vector<std::int32_t>{3, -4, 5});
    expect(list.sum == 4 && list.largest == 5 && list.negative_mask == 2, "summarises a list");
    std::puts(failures == 0 ? "unit tests passed" : "unit tests failed");
    return failures == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
