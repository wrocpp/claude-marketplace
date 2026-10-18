#include <fuzz_starter/driver.hpp>
#include <fuzz_starter/properties.hpp>

int main(int argc, char** argv) {
    return fuzz_starter::driver::run(argc, argv, &fuzz_starter::properties::parse_holds);
}
