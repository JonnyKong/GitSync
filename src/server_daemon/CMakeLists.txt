project(GitSync)
add_executable(server_daemon server_daemon.cpp)

add_executable(sync_main sync_main.cpp sync.cpp)     # TODO: Remove
include_directories(sync_main ${NDN_CXX_INCLUDE_DIRS})
target_link_libraries(sync_main ${NDN_CXX_LINK_LIBRARIES} ${Boost_LINK_LIBRARIES})

add_executable(storage_main storage_main.cpp storage.cpp)   # TODO: Remove
include_directories(storage_main ${MONGO_CXX_INCLUDE_DIRS} ${BSON_CXX_INCLUDE_DIRS})
target_link_libraries(storage_main ${MONGO_CXX_LINK_LIBRARIES} ${BSON_CXX_LINK_LIBRARIES})