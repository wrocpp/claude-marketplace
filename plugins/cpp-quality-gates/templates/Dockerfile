# Build image for the Linux sanitizer and coverage runs (scripts/linux-container.sh, IMAGE=<tag>).
# Pin the compiler tag you ship with; use gcc:latest in a nightly job to see new compilers early.
FROM gcc:16
RUN apt-get update \
 && apt-get install -y --no-install-recommends ninja-build python3 python3-pip python3-venv git ca-certificates \
 && pip install --break-system-packages cmake lizard gcovr universalmutator \
 && rm -rf /var/lib/apt/lists/*
