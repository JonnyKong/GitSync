#include "storage.hpp"
#include "logging.hpp"

#include <cstring>

#include <bsoncxx/builder/stream/document.hpp>
#include <bsoncxx/builder/basic/document.hpp>
#include <bsoncxx/builder/basic/kvp.hpp>
#include <bsoncxx/json.hpp>
#include <bsoncxx/stdx/make_unique.hpp>

#include <mongocxx/exception/operation_exception.hpp>
#include <mongocxx/uri.hpp>

using bsoncxx::builder::basic::kvp;
using bsoncxx::builder::basic::make_document;
using bsoncxx::builder::stream::finalize;

namespace ndn {
namespace gitsync {

Storage::Storage(const std::string &db /*= "gitsync"*/,
                 const std::string &collection /*= "objects"*/)
  : m_db(db)
  , m_collection(collection)
{
  // Create a unique index on hash on startup. The index is created if an index
  //  of the same specification does not already exist
  mongocxx::options::index index_options{};
  index_options.unique(true);
  conn[m_db][m_collection].create_index(make_document(kvp("hash", 1)), index_options);

  verbose("Unique index initialized\n");
}

bool
Storage::put(const std::string &hash, const uint8_t *data, size_t len)
{
  try {
    bsoncxx::builder::stream::document document{};
    bsoncxx::types::b_binary obj { bsoncxx::binary_sub_type::k_binary, uint32_t(len), data };
    document << "hash" << hash << "data" << obj;// << "len" << len;
    conn[m_db][m_collection].insert_one(document.view());
  } catch (const mongocxx::operation_exception& e) {
    fprintf(stderr, "ndn::gitsync::Storage: %s\n", e.what());
    return false;
  }

  verbose("Storage::put() len: %d\n", len);
  return true;
}

uint8_t*
Storage::get(const std::string &hash, size_t *len)
{
  bsoncxx::builder::stream::document document{};
  bsoncxx::stdx::optional<bsoncxx::document::value> maybe_result =
    conn[m_db][m_collection].find_one(document << "hash" << hash << finalize);

  if (!maybe_result) {
    fprintf(stderr, "ndn::gitsync::Storage: Not found\n");
    *len = 0;
    return nullptr;
  }

  auto obj = maybe_result->view()["data"].get_binary();
  void *data = malloc(obj.size * sizeof(uint8_t));
  memcpy(data, obj.bytes, obj.size);
  *len = obj.size;

  return (uint8_t*)data;
}

bool
Storage::exists(const std::string &hash)
{
  bsoncxx::builder::stream::document document{};
  bsoncxx::stdx::optional<bsoncxx::document::value> maybe_result =
    conn[m_db][m_collection].find_one(document << "hash" << hash << finalize);

  return maybe_result ? true : false;
}

bool
Storage::remove(const std::string &hash)
{
  bsoncxx::builder::stream::document document{};
  bsoncxx::stdx::optional<mongocxx::result::delete_result> result =
    conn[m_db][m_collection].delete_one(document << "hash" << hash << finalize);

  if (result)
    return true;
  else
    return false;
}


} // namespace gitsync
} // namespace ndn