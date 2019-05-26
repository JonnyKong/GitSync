#pragma once

uint8_t*
zlibDecode(const uint8_t* src, size_t len_src, size_t* len_dest);

std::string
hexStr(const uint8_t* data, size_t len);