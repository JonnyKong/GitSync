// For Storage testing
#include <iostream>
#include "storage.hpp"

namespace ndn {
namespace gitsync {

int Main(int argc, char **argv) {
  Storage s;
  uint8_t data[] = {
    0xFA, 0x11, 0x28, 0x33, 0xFA, 0x11, 0x28, 0x33,
    0xFA, 0x11, 0x28, 0x33, 0xFA, 0x11, 0x28, 0x33,
    0xFA, 0x11, 0x28, 0x33, 0xFA, 0x11, 0x28, 0x33,
    0xFA, 0x11, 0x28, 0x33, 0xFA, 0x11, 0x28, 0x33
  };
  std::string hash = "cf23df2207d99a74fbe169e3eba035e633b65d94";
  if (s.put(hash, data, 32)) {
    std::cout << "Inserted a document\n";
  }
}

} // namespace gitsync
} // namespace ndn



int main(int argc, char **argv) {
  return ndn::gitsync::Main(argc, argv);
}