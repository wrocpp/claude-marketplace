#!/bin/sh
# Install the test dependencies on Debian or Ubuntu (the gcc:16 image has the compiler and no clang or python3).
set -eu
apt-get update
apt-get install -y --no-install-recommends python3 clang git ca-certificates
