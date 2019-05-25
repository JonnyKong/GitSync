// Persistent storage with MongoDB
// Each document in the database have the following JSON format:
//  {
//    "_id" :   ObjectId("5cdf7467eaa8e044472b2982"),
//    "hash":   cf23df2207d99a74fbe169e3eba035e633b65d94
//    "data" :  BinData(0,"+hEoM/oRKDP6ESgz+hEoM/oRKDP6ESgz+hEoM/oRKDM=")
//  }

// Run "brew install mongodb" to install on macOS
// Run "mongod --config /usr/local/etc/mongod.conf" to start running MongoDB daemon
// Dependencies: mongocxx
// pkg-config --cflags --libs libmongocxx

// TODO: Whether should use per-repo collections?

#pragma once

#include <iostream>
#include <mongocxx/client.hpp>
#include <mongocxx/instance.hpp>

namespace ndn {
namespace gitsync {

class Storage {
public:
  // Create an index on hash on startup, if not already exists
  Storage(const std::string &db = "gitsync",
          const std::string &collection = "objects");

  // Write content to database by hash value, return false if document already
  //  exists.
  // Callee responsible for memory allocation & free.
  bool
  put(const std::string &hash, const uint8_t *bytes, size_t len);

  // Read content from database by hash value, return nullptr on failure.
  // Caller is responsible for memory allocation, callee responsible for free.
  uint8_t*
  get(const std::string &hash, size_t *len);

  // Return whether a hash already existed in the database.
  bool
  exists(const std::string &hash);

  // Remove content from database by hash value, return true if success.
  bool
  remove(const std::string &hash);

private:
  const std::string m_db;
  const std::string m_collection;

  mongocxx::instance inst{};
  mongocxx::client conn{ mongocxx::uri{} };   // Init with default localhost uri
};

} // namespace gitsync
} // namespace ndn