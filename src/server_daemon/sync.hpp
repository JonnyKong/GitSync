// Simplified version of vectorsync

#pragma once
#include <iostream>

#include <ndn-cxx/face.hpp>
#include <ndn-cxx/security/key-chain.hpp>
#include <ndn-cxx/util/time.hpp>


namespace ndn {
namespace gitsync {

using VersionVector = std::map<Name, uint64_t>;
using UpdateCallback = function<void(std::pair<Name, uint64_t>);

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
  publishData(Name prefix, uint64_t t = toUnixTimestamp(time::system_clock::now()).count());

private:
  // Encode a VersionVector object to ndn::Name, with each field separated by '_'.
  // Example: "PrefixFoo-10_PrefixBar-20_".
  // TODO: This encoding prevents prefixes to have "_" or "-" in them, better alternative?
  inline static Name
  encodeVector(const VersionVector& vector);

  // Decode the version vector string to VersionVector object.
  // TODO: This encoding prevents prefixes to have "_" or "-" in them, better alternative?
  inline static VersionVector
  decodeVector(const Name& vector_str);


private:
  Face& m_face;
  KeyChain& m_keychain;
  Name m_sync_prefix;
  UpdateCallback m_update_cb;
  VersionVector m_vector;
};

} // namespace gitsync
} // namespace ndn