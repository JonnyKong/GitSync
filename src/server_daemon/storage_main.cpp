// For Storage testing
#include <iostream>
#include <cstring>

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
  if (s.put(hash, data, sizeof(data))) {
    std::cout << "Inserted a document\n";
  }

  size_t len;
  uint8_t *ret = s.get(hash, &len);
  if (ret == nullptr) 
    std::cout << "Returned null ptr\n";
  else if (len != sizeof(data))
    std::cout << "Length different\n";
  else if (len == sizeof(data) && memcmp(data, ret, len) == 0)
    std::cout << "Success" << std::endl;

  free(ret);
  return 0;
}

} // namespace gitsync
} // namespace ndn



int main(int argc, char **argv) {
  return ndn::gitsync::Main(argc, argv);
}