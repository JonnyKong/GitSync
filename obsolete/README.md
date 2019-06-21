# GitSync

Git over NDN

### Dependencies

* [ndn-cxx](https://github.com/named-data/ndn-cxx) - NDN C++ library with eXperimental eXtensions
* [NFD](https://github.com/named-data/NFD) - Named Data Networking Forwarding Daemon
* [MongoDB](https://www.mongodb.com) - The MongoDB Database
* [mongocxx](http://mongocxx.org) - MongoDB C++ Driver
* [zlib 1.2.11](https://zlib.net) - Compression Library
* [PyMongo](https://api.mongodb.com/python/current/) - Python MongoDB API (For unit testing)

nfdc strategy set prefix /git strategy /localhost/nfd/strategy/multicast

### Build & Test with CMake

Perform out-of-source build in a separate directory:
```
cmake ..
make
make test
```