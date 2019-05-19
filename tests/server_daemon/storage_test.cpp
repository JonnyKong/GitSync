#include <iostream>

// For Storage testing
#include <iostream>
#include <cstring>

#include "storage.hpp"

namespace ndn {
namespace gitsync {

static uint8_t data[] = {
    0xFA, 0x11, 0x28, 0x33, 0xFA, 0x11, 0x28, 0x33,
    0xFA, 0x11, 0x28, 0x33, 0xFA, 0x11, 0x28, 0x33,
    0xFA, 0x11, 0x28, 0x33, 0xFA, 0x11, 0x28, 0x33,
    0xFA, 0x11, 0x28, 0x33, 0xFA, 0x11, 0x28, 0x33
  };
static std::string hash = "cf23df2207d99a74fbe169e3eba035e633b65d94";

int testInsertion() 
{
  Storage s;
  if (s.put(hash, data, sizeof(data))) {
    std::cout << "Inserted a document\n";
  }

  size_t len;
  uint8_t *ret = s.get(hash, &len);
  bool success = false;
  if (len == sizeof(data) && memcmp(data, ret, len) == 0)
    success = true;
    
  s.remove(hash);
  free(ret);
  if (success)
    return 0;
  else
    return -1;
}

int testDuplicateInsertion() 
{
  return 0;
}

int testObjectIntegrity() 
{

}



} // namespace gitsync
} // namespace ndn



int main(int argc, char **argv) {
  if (argc != 2)
    return 0;
  else if (strcmp(argv[1], "testInsertion"))
    return ndn::gitsync::testInsertion();
  else if (strcmp(argv[1], "testDuplicateInsertion"))
    return ndn::gitsync::testDuplicateInsertion();
}