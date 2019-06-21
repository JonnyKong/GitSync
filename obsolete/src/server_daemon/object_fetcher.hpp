#pragma once

#include <iostream>

#include "storage.hpp"

#include <ndn-cxx/face.hpp>
#include <ndn-cxx/security/key-chain.hpp>
#include <ndn-cxx/util/scheduler.hpp>

// ObjectFetcher: Fetch git objects from other servers, and serve git objects
//  for other servers

namespace ndn {
namespace gitsync {

class ObjectFetcher {
public:
  ObjectFetcher(Face& face, KeyChain& keychain, Storage& storage,
                const Name& object_prefix);

  // Fetch all non-available objects
  void
  fetchObject(const std::string& hash);

private:
  // Receive object data from other servers
  void
  onData(const Interest& interest, const Data& data);

  // Receive object interest from other servers
  void
  onInterest(const Name& prefix, const Interest& interest);

  // Need to retransmit
  void
  onTimeout(const Interest& interest, const std::string& reason);

  //
  void
  traverse(const std::string& hash, const std::string& expect_type = "");

  void
  traverseCommit(const uint8_t* bytes, size_t len);

  void
  traverseTree(const uint8_t* bytes, size_t len);

private:
  Face& m_face;
  KeyChain& m_keychain;
  Scheduler m_scheduler;
  Storage& m_storage;

  const Name m_object_prefix;
};


} // namespace gitsync
} // namespace ndn