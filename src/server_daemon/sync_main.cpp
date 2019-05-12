// For sync testing: Periodically publish in one branch of a  repo
#include <iostream>
#include <thread>

#include <ndn-cxx/face.hpp>
#include <ndn-cxx/security/key-chain.hpp>

#include "sync.hpp"

namespace ndn {
namespace gitsync {

void onUpdate(std::string repo, std::string branch, uint64_t timestamp) {
  std::cout << "App: Update:" << std::endl;
  std::cout << ">> Repo: " << repo << std::endl;
  std::cout << ">> Branch: " << branch << std::endl;
  std::cout << ">> Timestamp: " << timestamp << std::endl;
}

int Main(int argc, char **argv) {
  if (argc != 2) {
    printf("Usage: %s <branch_name>\n", argv[0]);
    exit(1);
  }

  std::string branch_name(argv[1]);
  Face face;
  KeyChain keychain;

  // Run sync on another thread
  Sync sync(face, keychain, "git", onUpdate);
  sync.subscribe("TestRepo");
  std::thread sync_t([&face] { face.processEvents(); });

  // Publish current time on branch_name on any user input
  std::string user_input;
  while (true) {
    std::getline(std::cin, user_input);
    if (sync.publishData("TestRepo", branch_name) == false) {
      std::cout << "Publish Failed\n";
    }
  }

  sync_t.join();
  return 0;
}

} // namespace gitsync
} // namespace ndn



int main(int argc, char **argv) {
  return ndn::gitsync::Main(argc, argv);
}