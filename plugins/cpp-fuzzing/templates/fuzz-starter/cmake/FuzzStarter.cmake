# Targets that reuse one property function. Everything a project file can influence (a corpus path,
# an alphabet, a message) is checked before it is written into generated C++.

set_property(GLOBAL PROPERTY JOB_POOLS fuzz_starter_constexpr=2)

set(FUZZ_STARTER_SANITIZER_FLAGS -fsanitize=address,undefined -fno-sanitize-recover=undefined -fno-omit-frame-pointer)

# Run-time targets get the sanitizers; the constexpr targets never do (see fuzz_starter_constexpr_flags).
function(fuzz_starter_instrument target)
  if(FUZZ_STARTER_SANITIZE)
    target_compile_options(${target} PRIVATE ${FUZZ_STARTER_SANITIZER_FLAGS})
    target_link_options(${target} PRIVATE ${FUZZ_STARTER_SANITIZER_FLAGS})
  endif()
endfunction()

# -fno-sanitize=all: compile-time evaluation has nothing to sanitise, and instrumentation can turn
# an expression that is constant without it into one that is not.
# The ops and loop limits (GCC) or the step limit (Clang) are the budget of one static_assert; the
# compiler stops with an error that names the option to raise.
function(fuzz_starter_constexpr_flags target)
  if(CMAKE_CXX_COMPILER_ID STREQUAL "Clang")
    target_compile_options(${target} PRIVATE -O0 -fno-sanitize=all -fconstexpr-steps=2000000000)
  else()
    target_compile_options(${target} PRIVATE -O0 -fno-sanitize=all
      -fconstexpr-ops-limit=4000000000 -fconstexpr-loop-limit=100000000)
  endif()
  set_target_properties(${target} PROPERTIES JOB_POOL_COMPILE fuzz_starter_constexpr)
endfunction()

function(fuzz_starter_require_plain text what)
  if(text MATCHES "[\"\\\\\n\r]")
    message(FATAL_ERROR "${what} contains a quote, a backslash or a newline: ${text}")
  endif()
endfunction()

# fuzz_<name>: harness tests/harness_<name>.cpp, also run over the corpus by ctest.
function(fuzz_starter_fuzz name)
  add_executable(fuzz_${name} tests/harness_${name}.cpp)
  target_link_libraries(fuzz_${name} PRIVATE fuzz_starter_core)
  fuzz_starter_instrument(fuzz_${name})
  add_test(NAME fuzz_${name} COMMAND fuzz_${name} ${CMAKE_CURRENT_SOURCE_DIR}/corpus)
  set_tests_properties(fuzz_${name} PROPERTIES LABELS fuzz-regression TIMEOUT 60)
endfunction()

# constexpr_corpus_<name>: a generated translation unit that #embeds every file of the directory and
# static_asserts the property on it. An empty file cannot be embedded into an array; it is asserted
# as an empty string.
function(fuzz_starter_constexpr_corpus name property directory)
  file(GLOB corpus CONFIGURE_DEPENDS ${directory}/*)
  set(body "#include <fuzz_starter/embedded.hpp>\n#include <fuzz_starter/properties.hpp>\n\nnamespace {\nusing namespace fuzz_starter;\n")
  set(index 0)
  foreach(file IN LISTS corpus)
    fuzz_starter_require_plain("${file}" "corpus path")
    file(SIZE ${file} size)
    get_filename_component(label ${file} NAME)
    if(size EQUAL 0)
      string(APPEND body "static_assert(properties::${property}(std::string_view{}), \"corpus replay: ${label}\");\n")
    else()
      string(APPEND body "constexpr unsigned char file_${index}[] = {\n#embed \"${file}\"\n};\n")
      string(APPEND body "static_assert(embedded_holds<&properties::${property}>(file_${index}), \"corpus replay: ${label}\");\n")
    endif()
    math(EXPR index "${index}+1")
  endforeach()
  string(APPEND body "}  // namespace\n\nint main() {}\n")
  file(GENERATE OUTPUT ${CMAKE_BINARY_DIR}/constexpr/corpus_${name}.cpp CONTENT "${body}")
  add_executable(constexpr_corpus_${name} ${CMAKE_BINARY_DIR}/constexpr/corpus_${name}.cpp)
  target_link_libraries(constexpr_corpus_${name} PRIVATE fuzz_starter_core)
  fuzz_starter_constexpr_flags(constexpr_corpus_${name})
  if(CMAKE_CXX_COMPILER_ID STREQUAL "Clang")
    target_compile_options(constexpr_corpus_${name} PRIVATE -Wno-c23-extensions)
  endif()
  set_source_files_properties(${CMAKE_BINARY_DIR}/constexpr/corpus_${name}.cpp PROPERTIES OBJECT_DEPENDS "${corpus}")
  add_test(NAME constexpr_corpus_${name} COMMAND constexpr_corpus_${name})
  set_tests_properties(constexpr_corpus_${name} PROPERTIES LABELS constexpr)
endfunction()

# constexpr_exhaustive_<name>: static_assert(for_all_texts(alphabet, length, property)). Each
# property gets its own executable so one check's memory use does not add to another's.
function(fuzz_starter_constexpr_exhaustive name property)
  cmake_parse_arguments(PARSE_ARGV 2 arg "" "ALPHABET;SHALLOW;DEEP;MESSAGE" "")
  fuzz_starter_require_plain("${arg_MESSAGE}" "exhaustive message")
  if(arg_ALPHABET MATCHES "\\)alpha\"")
    message(FATAL_ERROR "alphabet must not contain the raw string delimiter")
  endif()
  if(FUZZ_STARTER_DEPTH STREQUAL deep)
    set(length ${arg_DEEP})
  else()
    set(length ${arg_SHALLOW})
  endif()
  set(body "#include <fuzz_starter/exhaustive.hpp>\n#include <fuzz_starter/properties.hpp>\n\nstatic_assert(fuzz_starter::for_all_texts(R\"alpha(${arg_ALPHABET})alpha\", ${length}, &fuzz_starter::properties::${property}), \"${arg_MESSAGE}\");\n\nint main() {}\n")
  file(GENERATE OUTPUT ${CMAKE_BINARY_DIR}/constexpr/exhaustive_${name}.cpp CONTENT "${body}")
  add_executable(constexpr_exhaustive_${name} ${CMAKE_BINARY_DIR}/constexpr/exhaustive_${name}.cpp)
  target_link_libraries(constexpr_exhaustive_${name} PRIVATE fuzz_starter_core)
  fuzz_starter_constexpr_flags(constexpr_exhaustive_${name})
  add_test(NAME constexpr_exhaustive_${name} COMMAND constexpr_exhaustive_${name})
  set_tests_properties(constexpr_exhaustive_${name} PROPERTIES LABELS constexpr)
endfunction()
