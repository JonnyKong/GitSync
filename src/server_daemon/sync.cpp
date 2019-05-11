#include <iostream>
#include "boost/lexical_cast.hpp"

#include "sync.hpp"
#include "logging.hpp"

namespace ndn {
namespace gitsync {

using boost::lexical_cast;

Sync::Sync(Face& face, KeyChain& keychain, const Name& sync_prefix,
           const UpdateCallback& update_cb)
  : m_face(face)
  , m_keychain(keychain)
  , m_scheduler(face.getIoService())
  , m_sync_prefix(sync_prefix)
  , m_update_cb(update_cb)
  , m_random_generator(std::time(0))
  , m_retx_rand_ms(m_random_generator, boost::uniform_int<>(1000, 2000))
{
  verbose("Sync: Instance started\n");
  m_face.setInterestFilter(sync_prefix,
                           std::bind(&Sync::onSyncInterest, this, _1, _2),
                           [](const Name& prefix, const std::string& msg){});
  retxSyncInterest();
}

bool
Sync::publishData(Name prefix, uint64_t t)
{
  verbose("Sync: Publish Data: %s: %lld\n", prefix.toUri().c_str(), t);
  auto p = m_vector.find(prefix);
  if (p != m_vector.end() && p->second >= t) {
    return false;
  } else {
    p->second = t;
  }
  // TODO: Call m_update_cb on self-published data?

  retxSyncInterest();
}

inline std::string
Sync::encodeVector(const VersionVector& vector)
{
  std::string vector_str = "";
  for (auto e : vector)
    vector_str += (e.first.toUri() + "-" + std::to_string(e.second) + "_");
  return vector_str;
}

inline VersionVector
Sync::decodeVector(const std::string& vector_str)
{
  int start = 0;
  VersionVector vector;
  for (int i = 0; i < vector_str.size(); ++i) {
    if (vector_str[i] == '_') {
      std::string s = vector_str.substr(start, i - start);
      size_t sep = s.find("-");
      Name prefix = s.substr(0, sep);
      std::string t_str = s.substr(sep + 1);
      vector[prefix] = lexical_cast<uint64_t>(t_str);
    }
  }
  return vector;
}

void
Sync::retxSyncInterest()
{
  verbose("Sync: Retx Sync Interest\n");
  m_scheduler.cancelEvent(m_retx_event);

  Name i_name(m_sync_prefix);
  i_name.append(encodeVector(m_vector));
  Interest interest(i_name);
  m_face.expressInterest(interest,
                         std::bind([](){}),
                         std::bind([](){}),
                         std::bind([](){}));

  // Schedule next retransmission
  int delay_ms = m_retx_rand_ms();
  m_retx_event = m_scheduler.scheduleEvent(time::milliseconds(delay_ms),
                                           [this] {
    retxSyncInterest();
  });
}

void
Sync::onSyncInterest(const Name& prefix, const Interest& interest)
{
  verbose("Sync: Received Sync Interest\n");
  VersionVector other = decodeVector(interest.getName().get(-1).toUri());
  VersionVector diff;

  // Merge vector and extract differences
  for (auto e : other) {
    auto p = m_vector.find(e.first);
    if (p == m_vector.end() || e.second > p->second) {
      diff[e.first] = e.second;
      m_vector[e.first] = e.second;
    }
  }

  // Notify application
  for (auto e : diff)
    m_update_cb(e.first, e.second);
}


} // namespace gitsync
} // namespace ndn