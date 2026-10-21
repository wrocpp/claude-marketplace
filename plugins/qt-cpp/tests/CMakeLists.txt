# The fixtures of the qt-cpp plugin. Driven by tests/run.sh; see it for the contract.
cmake_minimum_required(VERSION 3.21)
project(qt_cpp_tests LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_AUTOMOC ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Debug)  # the one-thread and normalized-name checks need Q_ASSERT
endif()

find_package(Qt6 REQUIRED COMPONENTS Core Test)
find_package(Qt6 QUIET COMPONENTS Qml)

add_compile_options(-Wall -Wextra -Werror)
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/../include cpp)
enable_testing()

add_library(list_signals STATIC cpp/list_signals.cpp cpp/list_signals.hpp)
target_link_libraries(list_signals PUBLIC Qt6::Core)

function(qt_cpp_test name)
  add_executable(${name} ${ARGN})
  target_link_libraries(${name} PRIVATE list_signals Qt6::Core Qt6::Test)
  target_include_directories(${name} PRIVATE cpp)
  add_test(NAME ${name} COMMAND ${name})
  set_tests_properties(${name} PROPERTIES ENVIRONMENT "QT_QPA_PLATFORM=offscreen")
endfunction()

qt_cpp_test(contract_correct_model cpp/contract_correct_model.cpp)
qt_cpp_test(contract_flaws_detected cpp/contract_flaws_detected.cpp)
