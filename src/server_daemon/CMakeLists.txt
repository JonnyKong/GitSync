project(GitSync)
add_executable(server_daemon server_daemon.cpp)

add_executable(sync_main sync_main.cpp sync.cpp)     # TODO: Remove
include_directories(sync_main ${NDN_CXX_INCLUDE_DIRS})
link_directories(sync_main ${NDN_CXX_LIBRARY_DIRS})
target_link_libraries(sync_main ${NDN_CXX_LINK_LIBRARIES})