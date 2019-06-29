Dependencies
============
- Git
- MongoDB
- ndn-cxx
- NFD
- PyNDN2
- pymongo

Overview
========
GitSync contains 3 components: GitSync server deamon `gitsync-daemon`,
Git remote helper `git-remote-ndn` and GitSync CLI client `gitsync`.

The server daemon is a daemon that runs background, managing repos and syncing
up branches.

The remote helper is a middleware between `git` and `gitsync-daemon`.
It receives `push` and `pull` commands from `git`, completes these requests
by sending command Interests to `gitsync-daemon` and reports the result to
`git`.

The CLI client provides an user interface to track a repo and create a branch.

Execution
=========
This section shows an example on how to run GitSync locally.
```bash
# Start NFD
nfd-start

# Set multicast strategy
nfdc strategy set prefix /git strategy /localhost/nfd/strategy/multicast

# Start gitsync daemon with <command-prefix>
./gitsync-daemon <command-prefix>
# <command-prefix> is the prefix only used to send commands to this daemon

# Track a repo
./gitsync track-repo <repo-name>

# Create a branch with it custodian to be this node
./gitsync create-branch <repo-name> <branch-name>

# Add remote-url to local git repo
git remote add gitsync ndn::/git/<repo-name>

# Push local branch to daemon
git push gitsync <branch-name>
```

To connect to a different node, the only thing to do is configuring NFD.
```bash
nfdc face create udp://<other host>
nfdc route add /git <new-face>

# The following line is needed only when you want to push to a branch
# in the charge of that node
nfdc route add <new-node-command-prefix> <new-face>
```