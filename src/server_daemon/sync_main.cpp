// For sync testing: Periodically publish in one repo
#include <iostream>
#include <thread>

#include <ndn-cxx/face.hpp>
#include <ndn-cxx/security/key-chain.hpp>

#include "sync.hpp"

namespace ndn {
namespace gitsync {

void onUpdate(Name prefix, uint64_t timestamp) {
  std::cout << "onUpdate: " << prefix << ": " << timestamp << std::endl;
}

int Main(int argc, char **argv) {
  if (argc != 2) {
    printf("Usage: %s <repo_name>\n", argv[0]);
    exit(1);
  }

  std::string sync_prefix(argv[1]);
  Face face;
  KeyChain keychain;

  // Run sync on another thread
  Sync sync(face, keychain, sync_prefix, onUpdate);
  std::thread sync_t([&face] { face.processEvents(); });

  // Publish current time on sync_prefix on any user input
  std::string user_input;
  while (true) {
    std::getline(std::cin, user_input);
    sync.publishData(sync_prefix);
  }

  sync_t.join();
  return 0;
}

} // namespace gitsync
} // namespace ndn



int main(int argc, char **argv) {
  return ndn::gitsync::Main(argc, argv);
}