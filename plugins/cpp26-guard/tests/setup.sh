#!/bin/sh
# Installs what tests/run.sh needs on Debian or Ubuntu: python3, and GCC 16 when the distribution has it.
# GCC 16 may be absent from stable releases; the official gcc:16 image already carries it.
set -eu
if [ "$(id -u)" -eq 0 ]; then
    sudo=""
else
    sudo="sudo"
fi
$sudo apt-get update
$sudo apt-get install -y python3
if apt-cache show g++-16 >/dev/null 2>&1; then
    $sudo apt-get install -y g++-16
else
    echo "g++-16 is not packaged here; run the tests in the gcc:16 image or install GCC 16 yourself"
fi
