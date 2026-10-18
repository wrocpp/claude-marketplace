#!/bin/sh
# Install what tests/run.sh needs in a Debian or Ubuntu container that already has GCC 16
# (the gcc:16 image). Run as root. The distribution cmake is too old for import std with GCC
# (Debian 13 ships 3.31.6, which has no GCC support), so a newer CMake comes from the `cmake`
# wheel on PyPI, installed into a virtual environment at WROCPP_VENV.
set -eu

VENV=${WROCPP_VENV:-/opt/wrocpp-venv}
CMAKE_REQUIREMENT=${WROCPP_CMAKE_REQUIREMENT:-cmake>=4.0.3}

apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends ninja-build python3 python3-venv
python3 -m venv "$VENV"
"$VENV/bin/pip" install --quiet "$CMAKE_REQUIREMENT"
"$VENV/bin/cmake" --version | head -n 1
echo "run.sh picks $VENV/bin/cmake up by itself"
