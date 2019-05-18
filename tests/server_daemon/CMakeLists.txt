project(GitSync)
enable_testing()

add_executable(storage_test storage_test.cpp)
target_link_libraries(storage_test
                      server_daemon_lib
                      ${MONGO_CXX_LINK_LIBRARIES}
                      ${BSON_CXX_LINK_LIBRARIES})