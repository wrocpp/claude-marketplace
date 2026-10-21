#!/bin/sh
# Install the test dependencies on Debian or Ubuntu (the gcc:16 image has the compiler and no Qt, python3 or cmake).
set -eu
apt-get update
apt-get install -y --no-install-recommends python3 cmake ninja-build qt6-base-dev qt6-base-dev-tools qt6-declarative-dev
