enable_testing()

include_directories(${PROJECT_SOURCE_DIR}/src/remote_helper
                    ${PROJECT_SOURCE_DIR}/src/server_daemon
                    ${NDN_CXX_INCLUDE_DIRS}
                    ${MONGO_CXX_INCLUDE_DIRS}
                    ${BSON_CXX_INCLUDE_DIRS})

add_executable(storage_test storage_test.cpp)
target_link_libraries(storage_test
                      server_daemon_lib
                      ${MONGO_CXX_LINK_LIBRARIES}
                      ${BSON_CXX_LINK_LIBRARIES})

add_test(NAME testInsertion             COMMAND storage_test testInsertion)
add_test(NAME testDuplicateInsertion    COMMAND storage_test testDuplicateInsertion)
add_test(NAME testValidRemoval          COMMAND storage_test testValidRemoval)
add_test(NAME testInvalidRemoval        COMMAND storage_test testInvalidRemoval)
add_test(NAME testObjectIntegrity       COMMAND storage_test testObjectIntegrity)