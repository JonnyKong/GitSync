#include "storage.hpp"
#include "logging.hpp"

#include <bsoncxx/builder/stream/document.hpp>
#include <bsoncxx/json.hpp>

namespace ndn {
namespace gitsync {

Storage::Storage(const std::string &db /*= "gitsync"*/, 
                 const std::string &collection /*= "objects"*/)
  : m_db(db)
  , m_collection(collection)
{
  // TODO: Init hash if not already exists
  

  verbose("Storage initialized\n");
}

bool
Storage::put(const std::string &hash, uint8_t *bytes, size_t len)
{
  bsoncxx::builder::stream::document document{};
  bsoncxx::types::b_binary obj { bsoncxx::binary_sub_type::k_binary, uint32_t(len), bytes };
  document << "hash" << hash << "data" << obj;

  auto connection = conn[m_db][m_collection];
  connection.insert_one(document.view());

  // TODO: Should fail if hash already exists

  verbose("Storage::put()\n");
  return true;
}

uint8_t*
Storage::get(const std::string &hash, size_t *len)
{
  auto connection = conn[m_db][m_collection];
  bsoncxx::stdx::optional<bsoncxx::document::value> maybe_result =
    connection.find_one({});
  
  if (!maybe_result) {
    verbose("Storage::get() not found\n");
    return nullptr;
  }


}



} // namespace gitsync
} // namespace ndn