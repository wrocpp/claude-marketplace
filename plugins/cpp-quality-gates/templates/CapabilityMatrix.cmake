# Compiler capability matrix: one tiny translation unit per feature the project relies on.
#
#   include(CapabilityMatrix)
#   capability_matrix(DIR tests/capabilities FLAGS -std=c++26 -freflection)
#
# DIR/supported/*.cpp must compile; each is a ctest test "capability_<name>".
# DIR/absent/*.cpp must NOT compile; each is a ctest test "capability_absent_<name>" with
# WILL_FAIL, so a compiler upgrade that starts accepting it turns the test red and tells you
# the workaround can go. Both carry the ctest label "capability".
# The probes are syntax-only (-fsyntax-only): link-time and run-time behaviour is not covered.
function(capability_matrix)
  cmake_parse_arguments(ARG "" "DIR" "FLAGS;INCLUDE_DIRS" ${ARGN})
  if(NOT ARG_DIR)
    message(FATAL_ERROR "capability_matrix: DIR is required")
  endif()
  cmake_path(ABSOLUTE_PATH ARG_DIR BASE_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR} NORMALIZE)
  set(includes "")
  foreach(dir IN LISTS ARG_INCLUDE_DIRS)
    list(APPEND includes -I${dir})
  endforeach()
  foreach(kind IN ITEMS supported absent)
    file(GLOB probes CONFIGURE_DEPENDS ${ARG_DIR}/${kind}/*.cpp)
    foreach(probe IN LISTS probes)
      get_filename_component(name ${probe} NAME_WE)
      set(test capability_${name})
      if(kind STREQUAL absent)
        set(test capability_absent_${name})
      endif()
      add_test(NAME ${test} COMMAND ${CMAKE_CXX_COMPILER} ${ARG_FLAGS} ${includes} -fsyntax-only ${probe})
      set_tests_properties(${test} PROPERTIES LABELS capability)
      if(kind STREQUAL absent)
        set_tests_properties(${test} PROPERTIES WILL_FAIL TRUE)
      endif()
    endforeach()
  endforeach()
endfunction()
