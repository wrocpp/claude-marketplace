#!/bin/sh
# Installs what tests/run.sh needs in a Debian or Ubuntu container whose g++ is already GCC 16
# (for example the gcc:16 image). AFL++ is optional and not installed here; see
# templates/fuzz-starter/ops/Dockerfile.fuzz for an image that has it.
set -eu
as_root() { if [ "$(id -u)" -eq 0 ]; then "$@"; else sudo "$@"; fi; }
as_root apt-get update
as_root apt-get install -y --no-install-recommends cmake ninja-build python3 git ca-certificates
