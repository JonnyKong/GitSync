#include "object_fetcher.hpp"
#include "decode.hpp"
#include "logging.hpp"

#include <cassert>
#include <cstring>
#include <string.h>

namespace ndn {
namespace gitsync {


ObjectFetcher::ObjectFetcher(Face& face, KeyChain& keychain,
                             Storage& storage, const Name& object_prefix)
  : m_face(face)
  , m_keychain(keychain)
  , m_scheduler(face.getIoService())
  , m_storage(storage)
  , m_object_prefix(object_prefix)
{
  // Serve object for other servers
  m_face.setInterestFilter(object_prefix,
                           std::bind(&ObjectFetcher::onInterest, this, _1, _2),
                           [] (const Name& prefix, const std::string& msg) {});
}


void
ObjectFetcher::fetchObject(const std::string& hash)
{
  if (m_storage.exists(hash))
    return;

  Name i_name(m_object_prefix);
  i_name.append(hash);
  Interest interest(i_name);
  m_face.expressInterest(interest,
                         std::bind(&ObjectFetcher::onData, this, _1, _2),
                         std::bind(&ObjectFetcher::onTimeout, this, _1, "TIMEOUT"),
                         std::bind(&ObjectFetcher::onTimeout, this, _1, "NACK"));
  verbose("ObjectFetcher::fetchObject(): Send interest %s\n", interest.getName().toUri().c_str());
}


void
ObjectFetcher::onData(const Interest& interest, const Data& data)
{
  verbose("ObjectFetcher::onData(): Recv data\n");
  std::string hash = interest.getName()[-1].toUri();
  const uint8_t* bytes = data.getContent().value();
  size_t len = data.getContent().size();

  if (m_storage.exists(hash)) {
    return;
  } else {
    m_storage.put(hash, bytes, len);
  }

  traverse(hash);
}


void
ObjectFetcher::onInterest(const Name& prefix, const Interest& interest)
{
  verbose("Received interest: %s\n", interest.getName().toUri().c_str());
  std::string hash = interest.getName()[-1].toUri();

  if (!m_storage.exists(hash))
    return;

  size_t len;
  uint8_t* bytes = m_storage.get(hash, &len);

  Data data(interest.getName());
  data.setContent(bytes, len);
  m_keychain.sign(data);
  m_face.put(data);
  verbose("ObjectFetcher::onInterest(): Replying data\n");
}

void
ObjectFetcher::onTimeout(const Interest& interest, const std::string& reason)
{
  // TODO: How to re-transmit?
  m_face.expressInterest(interest,
                         std::bind(&ObjectFetcher::onData, this, _1, _2),
                         std::bind(&ObjectFetcher::onTimeout, this, _1, "TIMEOUT"),
                         std::bind(&ObjectFetcher::onTimeout, this, _1, "NACK"));
  verbose("ObjectFetcher::onTimeout(): Retx %s interest %s\n",
          reason.c_str(), interest.getName().toUri().c_str());
}

void
ObjectFetcher::traverse(const std::string& hash,
                        const std::string& expect_type /* = "" */)
{
  verbose("ObjectFetcher::traverse(): %s, %s\n", hash.c_str(), expect_type.c_str());

  // Decode header
  size_t len, len_decoded;
  uint8_t* bytes = m_storage.get(hash, &len);
  uint8_t* bytes_decoded = zlibDecode(bytes, len, &len_decoded);

  verbose("ObjectFetcher::traverse(): decoded %d bytes\n", len_decoded);

  size_t cursor_fast = 0, cursor_slow = 0;
  std::string content_type;
  size_t content_len;

  // Content type
  while (cursor_fast < len_decoded && bytes_decoded[cursor_fast] != ' ')
    cursor_fast++;
  content_type = std::string((const char*)bytes_decoded, cursor_fast - cursor_slow);
  cursor_fast = cursor_slow = cursor_fast + 1;

  // Content len
  while (cursor_fast < len_decoded && bytes_decoded[cursor_fast] != 0)
    cursor_fast++;
  content_len = atoi((const char*)(bytes_decoded + cursor_slow));
  cursor_fast = cursor_slow = cursor_fast + 1;

  verbose("ObjectFetcher::traverse(): decoded type: %s, len: %d\n", content_type.c_str(), content_len);

  // Length
  assert(content_len == (len_decoded - cursor_fast));
  // Type
  if (expect_type != "")
    assert(content_type == expect_type);

  // TODO: Check hash match

  // Recursion
  if (content_type == "commit")
    traverseCommit(bytes_decoded + cursor_fast, content_len);
  else if (content_type == "tree")
    traverseTree(bytes_decoded + cursor_fast, content_len);
  else
    assert(content_type == "blob");

  free(bytes);
  delete[] bytes_decoded;
}

void
ObjectFetcher::traverseCommit(const uint8_t* bytes, size_t len)
{
  verbose("ObjectFetcher::traverseCommit()\n");
  size_t cursor_fast = 0, cursor_slow = 0;
  while (cursor_fast < len) {
    // Jump over commit msg
    if (strncmp((const char*)bytes + cursor_fast, "tree",   4) != 0 &&
        strncmp((const char*)bytes + cursor_fast, "parent", 6) != 0) {
      break;
    }

    std::string expect_type, hash_name;

    // Decode expect_type
    while (cursor_fast < len && bytes[cursor_fast] != ' ')
      cursor_fast++;
    expect_type = std::string((const char*)bytes + cursor_slow, cursor_fast - cursor_slow);
    cursor_slow = cursor_fast = cursor_fast + 1;

    // Decode hash_name
    while (cursor_fast < len && bytes[cursor_fast] != '\n')
      cursor_fast++;
    hash_name = std::string((const char*)bytes + cursor_slow, cursor_fast - cursor_slow);
    cursor_slow = cursor_fast = cursor_fast + 1;

    if (expect_type == "parent")
      expect_type = "commit";

    if (hash_name.size() != 40)
      printf("FAIL\n");
    assert(hash_name.size() == 40);
    fetchObject(hash_name);
  }
}

void
ObjectFetcher::traverseTree(const uint8_t* bytes, size_t len)
{
  verbose("ObjectFetcher::traverseTree()\n");
  size_t cursor = 0;
  while (cursor < len) {
    size_t name_start = cursor + 1;
    while (name_start < len && bytes[name_start] != 0)
      name_start++;
    std::string hash_hex = hexStr(bytes + name_start + 1, 20);

    std::string expect_type;
    if (bytes[cursor] == 49)
      expect_type = "blob";
    else
      expect_type = "tree";

    if (hash_hex.size() != 40)
      printf("FAIL\n");
    assert(hash_hex.size() == 40);
    fetchObject(hash_hex);
    cursor = name_start + 21;
  }
}


} // namespace gitsync
} // namespace ndn