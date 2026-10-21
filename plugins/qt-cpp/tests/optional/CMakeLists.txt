# The fixtures that need reflect-moc (https://github.com/wrocpp/reflect-moc), GCC 16.2 and Qt 6.10. Driven by
# optional/run.sh, which passes -DREFLECT_MOC_DIR=<a checkout>. No moc runs here: reflect-moc replaces it.
cmake_minimum_required(VERSION 3.30)
project(qt_cpp_optional LANGUAGES CXX)

set(CMAKE_AUTOMOC OFF)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Debug)
endif()
enable_testing()

add_subdirectory(${REFLECT_MOC_DIR}/include/reflect_moc/qt reflect_moc_qt)

add_executable(reflect_moc_class_template_normalized reflect_moc_class_template_normalized.cpp)
target_link_libraries(reflect_moc_class_template_normalized PRIVATE reflect_moc::qt)
add_test(NAME reflect_moc_class_template_normalized COMMAND reflect_moc_class_template_normalized)

add_executable(reflect_moc_two_tus reflect_moc_two_tus_a.cpp reflect_moc_two_tus_b.cpp)
target_link_libraries(reflect_moc_two_tus PRIVATE reflect_moc::qt)
target_compile_options(reflect_moc_two_tus PRIVATE -flto -Wodr -Wlto-type-mismatch)
target_link_options(reflect_moc_two_tus PRIVATE -flto -Wodr -Wlto-type-mismatch -Werror)
add_test(NAME reflect_moc_two_tus COMMAND reflect_moc_two_tus)

set_tests_properties(reflect_moc_class_template_normalized reflect_moc_two_tus PROPERTIES ENVIRONMENT "QT_QPA_PLATFORM=offscreen")
