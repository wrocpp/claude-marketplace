#!/bin/sh
# Run mutate.py with universalmutator on PATH, creating a private venv when it is not installed.
# usage: mutate.sh SOURCE --build CMD --test CMD [options]   (see mutate.py)
set -eu
here=$(cd "$(dirname "$0")" && pwd)
if ! command -v mutate >/dev/null 2>&1; then
  venv=${QG_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/wrocpp/cpp-quality-gates-venv}
  [ -x "$venv/bin/mutate" ] || { mkdir -p "$venv" && python3 -m venv "$venv" && "$venv/bin/pip" install -q universalmutator; }
  PATH="$(cd "$venv/bin" && pwd):$PATH"
  export PATH
fi
exec python3 "$here/mutate.py" "$@"
