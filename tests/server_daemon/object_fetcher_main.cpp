// Integrated test for ObjectFetcher

#include <stdio.h>
#include <cstring>

#include <ndn-cxx/face.hpp>
#include <ndn-cxx/security/key-chain.hpp>
#include <ndn-cxx/util/scheduler.hpp>

#include "storage.hpp"
#include "object_fetcher.hpp"

namespace ndn {
namespace gitsync {

void
server()
{
  Face m_face;
  KeyChain m_keychain;
  Storage m_storage("gitsync", "objects_test_1");
  ObjectFetcher fetcher(m_face, m_keychain, m_storage, "/gitsync/objects");

  m_face.processEvents();
}

void
client(const std::string& hash)
{
  Face m_face;
  KeyChain m_keychain;
  Storage m_storage("gitsync", "objects_test_2");
  ObjectFetcher fetcher(m_face, m_keychain, m_storage, "/gitsync/objects");

  fetcher.fetchObject(hash);
  m_face.processEvents();
}


int
Main(int argc, char **argv)
{
  if (argc != 2 && argc != 3) {
    printf("Usage: %s <mode> [hash]\n", argv[0]);
    return 1;
  }

  if (strcmp(argv[1], "server") == 0)
    server();
  else
    client(argv[2]);

  return 0;
}

} // namespace gitsync
} // namespace ndn

int
main(int argc, char **argv)
{
  return ndn::gitsync::Main(argc, argv);
}