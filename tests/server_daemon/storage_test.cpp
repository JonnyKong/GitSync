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

// Should success if no existing entry with same hash value
int testInsertion() 
{
  bool success;
  Storage s;
  s.remove(hash);
  
  if (s.put(hash, data, sizeof(data)))
    success = true;
  else
    success = false;
  return success ? 0 : 1;
}

// Should fail if exists entry with same hash value
int testDuplicateInsertion() 
{
  bool success;
  Storage s;
  s.remove(hash);
  
  bool ret1 = s.put(hash, data, sizeof(data));
  bool ret2 = s.put(hash, data, sizeof(data));

  if (ret1 == true && ret2 == false)
    success = true;
  else
    success = false;
  return success ? 0 : 1;
}

// Should success for removal of already existing entry
int testValidRemoval() 
{
  bool success;
  Storage s;
  s.put(hash, data, sizeof(data));
  
  bool ret = s.remove(hash);
  if (ret)
    success = true;
  else
    success = false;
  return success ? 0 : 1;
}

// Should also success for removal of not existing entry
int testInvalidRemoval()
{
  bool success;
  Storage s;
  s.remove(hash);

  bool ret = s.remove(hash);
  if (ret)
    success = true;
  else
    success = false;
  return success ? 0 : -1;
}

// Should return the same data content
int testGetValidObject() 
{
  bool success;
  Storage s;
  s.put(hash, data, sizeof(data));

  size_t len;
  uint8_t *ret = s.get(hash, &len);
  
  if (len == sizeof(data) && memcmp(data, ret, len) == 0)
    success = true;
  else
    success = false;
  free(ret);
  return success ? 0 : 1;
}

// Should fail if read non-existent object
int testGetInvalidObject()
{
  bool success;
  Storage s;
  s.remove(hash);

  size_t len;
  uint8_t *ret = s.get(hash, &len);
  
  if (ret == nullptr && len == 0)
    success = true;
  else
    success = false;

  return success ? 0 : 1;
}

} // namespace gitsync
} // namespace ndn



int main(int argc, char **argv) {
  if (argc != 2)
    return 0;
  
  else if (strcmp(argv[1], "testInsertion") == 0)
    return ndn::gitsync::testInsertion();
  
  else if (strcmp(argv[1], "testDuplicateInsertion") == 0)
    return ndn::gitsync::testDuplicateInsertion();
  
  else if (strcmp(argv[1], "testValidRemoval") == 0)
    return ndn::gitsync::testValidRemoval();
  
  else if (strcmp(argv[1], "testInvalidRemoval") == 0)
    return ndn::gitsync::testInvalidRemoval();
  
  else if (strcmp(argv[1], "testGetValidObject") == 0)
    return ndn::gitsync::testGetValidObject();
  
  else if (strcmp(argv[1], "testGetInvalidObject") == 0)
    return ndn::gitsync::testGetInvalidObject();

  else
    return 0;
}