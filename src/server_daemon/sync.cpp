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
Sync::publishData(std::string repo, std::string branch, uint64_t t)
{
  // TODO: mutex lock
  if (t == 0)
    t = toUnixTimestamp(time::system_clock::now()).count();
  verbose("Sync: Publishing: %s/%s: %lu\n", repo.c_str(), branch.c_str(), t);

  if (m_vector.find(repo) == m_vector.end())
    return false;

  auto p = m_vector[repo].find(branch);
  if (p != m_vector[repo].end() && p->second >= t) {
    return false;
  } else {
    m_vector[repo][branch] = t;
  }
  // TODO: Call m_update_cb on self-published data?
  return true;
}

void
Sync::subscribe(std::string repo)
{
  m_subscribed_repo.insert(repo);
  m_vector[repo] = VersionVector();
}

inline std::string
Sync::encodeVector(const VersionVector& vector)
{
  std::string vector_str = "";
  for (auto e : vector)
    vector_str += (e.first + "-" + std::to_string(e.second) + "_");
  return vector_str;
}

inline VersionVector
Sync::decodeVector(const std::string& vector_str)
{
  int start = 0;
  VersionVector vector;
  for (size_t i = 0; i < vector_str.size(); ++i) {
    if (vector_str[i] == '_') {
      std::string s = vector_str.substr(start, i - start);
      size_t sep = s.find("-");
      std::string prefix = s.substr(0, sep);
      std::string t_str = s.substr(sep + 1);
      vector[prefix] = lexical_cast<uint64_t>(t_str);
    }
  }
  return vector;
}

void
Sync::retxSyncInterest()
{
  m_scheduler.cancelAllEvents();

  for (auto repo : m_vector) {
    // If vector for a repo is empty, doesn't have to send anything
    if (repo.second.size() == 0)
      continue;

    Name i_name(m_sync_prefix);
    i_name.append(repo.first);
    i_name.append("sync");
    i_name.append(encodeVector(repo.second));
    Interest interest(i_name);
    m_face.expressInterest(interest,
                           std::bind([](){}),
                           std::bind([](){}),
                           std::bind([](){}));
    verbose("Sync: Retx Sync Interest: %s\n", i_name.toUri().c_str());
  }

  // Schedule next retransmission
  int delay_ms = m_retx_rand_ms();
  m_scheduler.schedule(time::milliseconds(delay_ms), [this] {
    retxSyncInterest();
  });
}

void
Sync::onSyncInterest(const Name& prefix, const Interest& interest)
{
  // verbose("Received interest: %s\n", interest.getName().toUri().c_str());
  std::string repo = interest.getName().get(1).toUri();

  // verbose("Sync: Received Sync Interest for repo %s\n", repo.c_str());
  VersionVector other;
  if (interest.getName().size() == 4)
    other = decodeVector(interest.getName().get(-1).toUri());
  VersionVector diff;

  // Merge vector and extract differences
  for (auto e : other) {
    auto p = m_vector[repo].find(e.first);
    if (p == m_vector[repo].end() || e.second > p->second) {
      diff[e.first] = e.second;
      m_vector[repo][e.first] = e.second;
    }
  }

  // Notify application
  for (auto e : diff)
    m_update_cb(repo, e.first, e.second);
}


} // namespace gitsync
} // namespace ndn