cmake_minimum_required(VERSION 3.28)
project(fuzz_starter LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 26)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

set(FUZZ_STARTER_PLANTED_BUG none CACHE STRING
    "Plant a defect to see the checks fail: none overflow oob uninit null divzero shift roundtrip runtime_only")
set_property(CACHE FUZZ_STARTER_PLANTED_BUG PROPERTY STRINGS none overflow oob uninit null divzero shift roundtrip runtime_only)
set(FUZZ_STARTER_DEPTH shallow CACHE STRING "Bounds of the compile-time exhaustive checks: shallow or deep")
set_property(CACHE FUZZ_STARTER_DEPTH PROPERTY STRINGS shallow deep)
option(FUZZ_STARTER_SANITIZE "Build the unit test and the fuzz binaries with ASan and UBSan" OFF)

set(planted_bugs none overflow oob uninit null divzero shift roundtrip runtime_only)
list(FIND planted_bugs "${FUZZ_STARTER_PLANTED_BUG}" bug_number)
if(bug_number EQUAL -1)
  message(FATAL_ERROR "FUZZ_STARTER_PLANTED_BUG must be one of: ${planted_bugs}")
endif()
if(NOT FUZZ_STARTER_DEPTH STREQUAL shallow AND NOT FUZZ_STARTER_DEPTH STREQUAL deep)
  message(FATAL_ERROR "FUZZ_STARTER_DEPTH must be shallow or deep")
endif()

include(cmake/FuzzStarter.cmake)

add_library(fuzz_starter_core INTERFACE)
target_include_directories(fuzz_starter_core INTERFACE ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_compile_definitions(fuzz_starter_core INTERFACE FUZZ_STARTER_BUG=${bug_number})
target_compile_options(fuzz_starter_core INTERFACE -Wall -Wextra -Wpedantic -Werror)
if(CMAKE_CXX_COMPILER MATCHES "afl-")
  # The persistent-mode macros of AFL++ are GNU statement expressions.
  target_compile_options(fuzz_starter_core INTERFACE -Wno-pedantic)
endif()

enable_testing()

add_executable(unit_test tests/unit_test.cpp)
target_link_libraries(unit_test PRIVATE fuzz_starter_core)
fuzz_starter_instrument(unit_test)
add_test(NAME unit_test COMMAND unit_test)

# One property function per module; the same function feeds every target below.
fuzz_starter_fuzz(parse)
fuzz_starter_fuzz(summary)

fuzz_starter_constexpr_corpus(parse parse_holds ${CMAKE_CURRENT_SOURCE_DIR}/corpus)
fuzz_starter_constexpr_corpus(summary summary_holds ${CMAKE_CURRENT_SOURCE_DIR}/corpus)

# One translation unit per property: a bounded-exhaustive check can run out of memory on its own.
fuzz_starter_constexpr_exhaustive(parse parse_holds
  ALPHABET "0-,9" SHALLOW 4 DEEP 6
  MESSAGE "a short text breaks parse_list or format_list")
fuzz_starter_constexpr_exhaustive(summary summary_holds
  ALPHABET "0-,9" SHALLOW 4 DEEP 6
  MESSAGE "a short text breaks summarise")
