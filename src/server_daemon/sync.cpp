#include <iostream>
#include "boost/lexical_cast.hpp" 

#include "sync.hpp"

namespace ndn {
namespace gitsync {

using boost::lexical_cast; 

Sync::Sync(Face& face, KeyChain& keychain, const Name& sync_prefix,
           const UpdateCallback& update_cb)
  : m_face(face)
  , m_keychain(keychain)
  , m_sync_prefix(sync_prefix)
  , m_update_cb(update_cb)
{

}

bool
Sync::publishData(Name prefix, uint64_t t)
{

}

inline static Name
encodeVector(const VersionVector& vector)
{
  std::string vector_str = "";
  for (auto e : vector)
    vector_str += (e.first.toUri() + "-" + std::to_string(e.second) + "_");
  return Name(vector_str);
}

inline static VersionVector
decodeVector(const Name& vector_str)
{
  int start = 0;
  VersionVector vector;
  for (int i = 0; i < vector_str.toUri().size(); ++i) {
    if (vector_str.toUri()[i] == '_') {
      std::string s = vector_str.toUri().substr(start, i - start);
      size_t sep = s.find("-");
      Name prefix = s.substr(0, sep);
      std::string t_str = s.substr(sep + 1);
      vector[prefix] = lexical_cast<uint64_t>(t_str);
    }
  }
  return vector;
}

} // namespace gitsync
} // namespace ndn