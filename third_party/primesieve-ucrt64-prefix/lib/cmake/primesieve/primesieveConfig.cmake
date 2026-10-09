# ====================================================================
# The primesieve CMake configuration file
#
# Usage from an external project:
#     In your CMakeLists.txt, add these lines:
#
#     find_package(primesieve REQUIRED)
#     target_link_libraries(your_program primesieve::primesieve)
#
#     To link against the static libprimesieve use:
#
#     find_package(primesieve REQUIRED static)
#     target_link_libraries(your_program primesieve::primesieve)
#
# ====================================================================


####### Expanded from @PACKAGE_INIT@ by configure_package_config_file() #######
####### Any changes to this file will be overwritten by the next CMake run ####
####### The input file was primesieveConfig.cmake.in                            ########

get_filename_component(PACKAGE_PREFIX_DIR "${CMAKE_CURRENT_LIST_DIR}/../../../" ABSOLUTE)

macro(set_and_check _var _file)
  set(${_var} "${_file}")
  if(NOT EXISTS "${_file}")
    message(FATAL_ERROR "File or directory ${_file} referenced by variable ${_var} does not exist !")
  endif()
endmacro()

macro(check_required_components _NAME)
  foreach(comp ${${_NAME}_FIND_COMPONENTS})
    if(NOT ${_NAME}_${comp}_FOUND)
      if(${_NAME}_FIND_REQUIRED_${comp})
        set(${_NAME}_FOUND FALSE)
      endif()
    endif()
  endforeach()
endmacro()

####################################################################################

# Nothing to do if primesieve is included as a subdirectory in
# another project that uses CMake as its build system.
if(TARGET primesieve::primesieve)
    return()
endif()

include(CMakeFindDependencyMacro)
find_dependency(Threads QUIET)

if(ON AND OFF)
    if(primesieve_FIND_COMPONENTS)
        string(TOLOWER "${primesieve_FIND_COMPONENTS}" LOWER_COMPONENTS)
        if(LOWER_COMPONENTS STREQUAL "static")
            set(primesieve_STATIC TRUE)
        endif()
    endif()
elseif(ON)
    set(primesieve_STATIC TRUE)
endif()

if(primesieve_STATIC)
    include("${CMAKE_CURRENT_LIST_DIR}/primesieveStatic.cmake")
    add_library(primesieve::primesieve INTERFACE IMPORTED)
    set_target_properties(primesieve::primesieve PROPERTIES INTERFACE_LINK_LIBRARIES "primesieve::libprimesieve-static")
else()
    include("${CMAKE_CURRENT_LIST_DIR}/primesieveShared.cmake")
    add_library(primesieve::primesieve INTERFACE IMPORTED)
    set_target_properties(primesieve::primesieve PROPERTIES INTERFACE_LINK_LIBRARIES "primesieve::libprimesieve")
endif()
