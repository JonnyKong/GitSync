#include <iostream>
#include <sstream>
#include <vector>
#include <cstring>

#include "zlib.h"

#define CHUNK 16384

// Callee responsible for free
uint8_t*
zlibDecode(const uint8_t* src, size_t len_src, size_t* len_dest)
{
  int ret;
  unsigned have;
  z_stream strm;
  unsigned char in[CHUNK];
  unsigned char out[CHUNK];

  /* allocate inflate state */
  strm.zalloc = Z_NULL;
  strm.zfree = Z_NULL;
  strm.opaque = Z_NULL;
  strm.avail_in = 0;
  strm.next_in = Z_NULL;
  ret = inflateInit(&strm);
  if (ret != Z_OK)
    return NULL;

  size_t cursor = 0;
  std::vector<char> result;

  /* decompress until deflate stream ends or end of file */
  do {
    // strm.avail_in = fread(in, 1, CHUNK, source);
    strm.avail_in = (len_src - cursor) < CHUNK ? (len_src - cursor) : CHUNK;
    memset(in, 0, CHUNK);
    memcpy(in, src + cursor, strm.avail_in);
    cursor += strm.avail_in;
    if (strm.avail_in == 0)
      break;
    strm.next_in = in;

    /* run inflate() on input until output buffer not full */
    do {
      strm.avail_out = CHUNK;
      strm.next_out = out;
      ret = inflate(&strm, Z_NO_FLUSH);
      assert(ret != Z_STREAM_ERROR);  /* state not clobbered */
      switch (ret) {
        case Z_NEED_DICT:
            ret = Z_DATA_ERROR;     /* and fall through */
        case Z_DATA_ERROR:
        case Z_MEM_ERROR:
            (void)inflateEnd(&strm);
            return nullptr;
      }
      have = CHUNK - strm.avail_out;
      // if (fwrite(out, 1, have, stdout) != have) {
      //     (void)inflateEnd(&strm);
      //     return nullptr;
      // }
      result.insert(result.end(), out, out + have);
    } while (strm.avail_out == 0);

    /* done when inflate() says it's done */
  } while (ret != Z_STREAM_END);

  /* clean up and return */
  uint8_t *bytes = new uint8_t[result.size()];
  memcpy(bytes, result.data(), result.size());
  (void)inflateEnd(&strm);

  if (ret == Z_STREAM_END) {
    *len_dest = result.size();
    return bytes;
  } else {
    *len_dest = 0;
    free(bytes);
    return nullptr;
  }
}

// Convert byte blob to hex string
std::string
hexStr(const uint8_t* data, size_t len)
{
  char hex_str[len * 2 + 1];
  for (size_t i = 0; i < len; ++i) {
    sprintf(hex_str + i * 2, "%02x", data[i]);
  }
  hex_str[len * 2] = 0;
  return std::string(hex_str);
}