cmake_minimum_required(VERSION 3.23)
project(quality_gates_sample CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
enable_testing()
include(${CMAKE_CURRENT_SOURCE_DIR}/../../templates/CapabilityMatrix.cmake)

add_library(sample src/calc.cpp src/saturate.cpp)
target_include_directories(sample PUBLIC src)

add_executable(calc_test tests/calc_test.cpp)
target_link_libraries(calc_test PRIVATE sample)
add_test(NAME calc_test COMMAND calc_test)

add_executable(saturate_test tests/saturate_test.cpp)
target_link_libraries(saturate_test PRIVATE sample)
add_test(NAME saturate_test COMMAND saturate_test)
set_tests_properties(calc_test saturate_test PROPERTIES LABELS unit)

foreach(planted IN ITEMS heap_overflow signed_overflow leak)
  add_executable(planted_${planted} EXCLUDE_FROM_ALL tests/planted/${planted}.cpp)
endforeach()
find_package(Threads REQUIRED)
add_executable(planted_race EXCLUDE_FROM_ALL tests/planted/race.cpp)
target_link_libraries(planted_race PRIVATE Threads::Threads)

capability_matrix(DIR tests/capabilities FLAGS -std=c++20)
