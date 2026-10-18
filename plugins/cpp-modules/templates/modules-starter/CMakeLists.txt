cmake_minimum_required(VERSION 3.30)

# Before project(): CMake reads the gate while it detects the compiler.
include(cmake/ImportStdGate.cmake)

project(modules_starter VERSION 0.1.0 LANGUAGES CXX)

set(STARTER_CXX_STANDARD 23 CACHE STRING "C++ standard of the starter, 23 or 26")
set(CMAKE_CXX_STANDARD ${STARTER_CXX_STANDARD})
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_CXX_SCAN_FOR_MODULES ON)
set(CMAKE_CXX_MODULE_STD ON)

add_library(starter_flags INTERFACE)
target_compile_options(starter_flags INTERFACE -Wall -Wextra -Werror)

add_library(greeter)
target_sources(greeter
  PUBLIC FILE_SET CXX_MODULES BASE_DIRS src FILES src/greeter/greeter.cppm
  PRIVATE src/greeter/greeter.cpp)
target_link_libraries(greeter PUBLIC starter_flags)

add_executable(starter app/main.cpp)
target_link_libraries(starter PRIVATE greeter)

enable_testing()
add_executable(greeter_test tests/greeter_test.cpp)
target_link_libraries(greeter_test PRIVATE greeter)
add_test(NAME greeter_test COMMAND greeter_test)
