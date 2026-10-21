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
qt_cpp_test(row_index cpp/row_index.cpp)
qt_cpp_test(list_ranges_and_edits cpp/list_ranges_and_edits.cpp)
qt_cpp_test(dependent_base_connect cpp/traps/dependent_base_connect.cpp)
qt_cpp_test(normalized_names cpp/traps/normalized_names.cpp)
# What must compile: the controls of the fixtures that must not.
file(GLOB ACCEPTED CONFIGURE_DEPENDS cpp/accept/*.cpp)
add_library(accepted OBJECT ${ACCEPTED})
target_link_libraries(accepted PRIVATE list_signals Qt6::Core)

# Two translation units that agree, linked with the flags that make a disagreement an error.
add_executable(odr_consistent cpp/odr/a.cpp cpp/odr/b.cpp)
target_compile_options(odr_consistent PRIVATE -flto -Wodr -Wlto-type-mismatch)
target_link_options(odr_consistent PRIVATE -flto -Wodr -Wlto-type-mismatch -Werror)
set_target_properties(odr_consistent PROPERTIES AUTOMOC OFF)
add_test(NAME odr_consistent COMMAND odr_consistent)

# What must not compile (or link): one target each, built only by tests/check_reject.py, which reads the
# `// expect-error: <regex>` line at the top of the file and fails when the build succeeds or says something else.
file(GLOB REJECTED CONFIGURE_DEPENDS cpp/reject/*.cpp)
foreach(source ${REJECTED})
  get_filename_component(stem ${source} NAME_WE)
  add_library(reject_${stem} OBJECT EXCLUDE_FROM_ALL ${source})
  target_link_libraries(reject_${stem} PRIVATE list_signals Qt6::Core)
  # *_by_moc.cpp is built with moc: the rejection is moc's, and it comes before the compiler runs.
  if(NOT stem MATCHES "_by_moc$")
    set_target_properties(reject_${stem} PROPERTIES AUTOMOC OFF)
  endif()
endforeach()
add_executable(reject_odr_violation EXCLUDE_FROM_ALL cpp/reject/odr_violation/a.cpp cpp/reject/odr_violation/b.cpp)
target_compile_options(reject_odr_violation PRIVATE -flto -Wodr -Wlto-type-mismatch)
target_link_options(reject_odr_violation PRIVATE -flto -Wodr -Wlto-type-mismatch -Werror)
set_target_properties(reject_odr_violation PROPERTIES AUTOMOC OFF)
