# GitSync

Git over NDN

### Dependencies

* [ndn-cxx](https://github.com/named-data/ndn-cxx) - NDN C++ library with eXperimental eXtensions
* [NFD](https://github.com/named-data/NFD) - Named Data Networking Forwarding Daemon
* [MongoDB](https://www.mongodb.com) - The MongoDB Database
* [mongocxx](http://mongocxx.org) - MongoDB C++ Driver

### Build & Test with CMake

Perform out-of-source build in a separate directory:
```
cmake ..
make
make test
```