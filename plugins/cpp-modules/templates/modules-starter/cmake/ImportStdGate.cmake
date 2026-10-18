# The CMAKE_EXPERIMENTAL_CXX_IMPORT_STD gate of the CMake in use. Include it before project().
# Measured with GCC 16.2.0 on CMake 3.30.9 to 4.4.4: see the cmake-import-std skill. A newer CMake may need a new UUID:
# python3 scripts/find_import_std_gate.py prints it.
if(CMAKE_VERSION VERSION_GREATER_EQUAL 4.4)
  set(CMAKE_EXPERIMENTAL_CXX_IMPORT_STD f35a9ac6-8463-4d38-8eec-5d6008153e7d)
elseif(CMAKE_VERSION VERSION_GREATER_EQUAL 4.3)
  set(CMAKE_EXPERIMENTAL_CXX_IMPORT_STD 451f2fe2-a8a2-47c3-bc32-94786d8fc91b)
elseif(CMAKE_VERSION VERSION_GREATER_EQUAL 4.0.3 OR CMAKE_VERSION VERSION_EQUAL 3.31.10)
  set(CMAKE_EXPERIMENTAL_CXX_IMPORT_STD d0edc3af-4c50-42ea-a356-e2862fe7a444)
else()
  message(FATAL_ERROR "import std with GCC needs CMake 3.31.10 or 4.0.3 and newer, found ${CMAKE_VERSION}")
endif()
