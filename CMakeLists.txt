cmake_minimum_required(VERSION 3.10.0)
project(GitSync)
enable_testing()

# Enforce out-of-source build
if (${CMAKE_SOURCE_DIR} STREQUAL ${CMAKE_BINARY_DIR})
    message(FATAL_ERROR "In-source builds not allowed.
    Please make a new directory (called a build directory) and run CMake from there.
    You may need to remove CMakeCache.txt." )
endif()
# Output binaries to a sub directory "bin"
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++14 -Wall")
set(CMAKE_CXX_FLAGS_DEBUG "-O0 -ggdb")
set(CMAKE_CXX_FLAGS_RELEASE "-O3")

add_compile_definitions(_GNU_SOURCE)

INCLUDE(FindPkgConfig)
pkg_check_modules(NDN_CXX libndn-cxx)               # ndn-cxx
pkg_check_modules(MONGO_CXX REQUIRED libmongocxx)   # mongocxx
pkg_check_modules(BSON_CXX REQUIRED libbsoncxx)     # mongocxx

find_package(Boost COMPONENTS system filesystem random REQUIRED)


add_subdirectory(src)
add_subdirectory(tests)