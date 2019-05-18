project(GitSync)

include_directories(${NDN_CXX_INCLUDE_DIRS}
                    ${MONGO_CXX_INCLUDE_DIRS}
                    ${BSON_CXX_INCLUDE_DIRS})

add_library(server_daemon_lib sync.cpp storage.cpp)
add_executable(server_daemon server_daemon.cpp)
target_link_libraries(server_daemon 
                      server_daemon_lib
                      ${NDN_CXX_LINK_LIBRARIES}
                      ${MONGO_CXX_LINK_LIBRARIES}
                      ${BSON_CXX_LINK_LIBRARIES}
                      ${Boost_LINK_LIBRARIES})

# TODO: Remove
add_executable(sync_main sync_main.cpp)
target_link_libraries(sync_main 
                      server_daemon_lib
                      ${NDN_CXX_LINK_LIBRARIES}
                      ${Boost_LINK_LIBRARIES})
# TODO: Remove
add_executable(storage_main storage_main.cpp)
target_link_libraries(storage_main 
                      server_daemon_lib
                      ${MONGO_CXX_LINK_LIBRARIES}
                      ${BSON_CXX_LINK_LIBRARIES})