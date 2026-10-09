#----------------------------------------------------------------
# Generated CMake target import file for configuration "Release".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "primesieve::libprimesieve-static" for configuration "Release"
set_property(TARGET primesieve::libprimesieve-static APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(primesieve::libprimesieve-static PROPERTIES
  IMPORTED_LINK_INTERFACE_LANGUAGES_RELEASE "CXX"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/libprimesieve.a"
  )

list(APPEND _cmake_import_check_targets primesieve::libprimesieve-static )
list(APPEND _cmake_import_check_files_for_primesieve::libprimesieve-static "${_IMPORT_PREFIX}/lib/libprimesieve.a" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
