// Simplified version of vectorsync
#pragma once

#include <iostream>
#include <boost/random.hpp>

#include <ndn-cxx/face.hpp>
#include <ndn-cxx/security/key-chain.hpp>
#include <ndn-cxx/util/scheduler.hpp>
#include <ndn-cxx/util/time.hpp>


namespace ndn {
namespace gitsync {

using VersionVector = std::map<std::string, uint64_t>;
using UpdateCallback = function<void(std::string, std::string, uint64_t)>;  // (repo, branch, timestamp)

class Sync {
public:
  // Need higher layers to pass a callback
  Sync(Face& face, KeyChain& keychain, const Name& sync_prefix,
       const UpdateCallback& update_cb);

  // Publish data to a given prefix, and return whether the operation succeeded.
  // It may fail if the given timestamp is smaller or equal to the existing
  //  timestamp. Create the prefix if it doesn't exist.
  // Need higher levels to enforce write permission.
  bool
  publishData(std::string repo, std::string branch, uint64_t t = 0);

  // Subscribe to a repo.
  void
  subscribe(std::string repo);


private:
  // Encode a VersionVector object to ndn::Name, with each field separated by '_'.
  // Example: "PrefixFoo-10_PrefixBar-20_".
  // TODO: This encoding prevents prefixes to have "_" or "-" in them, better alternative?
  inline static std::string
  encodeVector(const VersionVector& vector);

  // Decode the version vector string to VersionVector object.
  // TODO: This encoding prevents prefixes to have "_" or "-" in them, better alternative?
  inline static VersionVector
  decodeVector(const std::string& vector_str);

  // Transmit 1 sync interest for each non-empty repo periodically. This function 
  //  will re-schedule itself, but when called directly, it will send out a sync 
  //  interest immediately and re-schedule the subsequent events.
  // Interest format: /<sync_prefix>/<repo_name>/sync/<sync_vector>
  void
  retxSyncInterest();

  // Merge local vector, and notify the application about the latest updates
  void
  onSyncInterest(const Name& prefix, const Interest& interest);


private:
  Face& m_face;
  KeyChain& m_keychain;
  Scheduler m_scheduler;
  Name m_sync_prefix;
  UpdateCallback m_update_cb;
  std::map<std::string, VersionVector> m_vector;
  std::set<std::string> m_subscribed_repo;

  boost::mt19937 m_random_generator;
  boost::variate_generator<boost::mt19937&, boost::uniform_int<>> m_retx_rand_ms;  // ms
};

} // namespace gitsync
} // namespace ndn