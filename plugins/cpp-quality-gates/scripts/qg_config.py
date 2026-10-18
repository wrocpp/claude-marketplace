import json
import os
import pathlib
import sys

CONFIG_PATH = pathlib.Path(".claude/cpp-quality-gates.json")


def load(path=None):
    path = pathlib.Path(path) if path else CONFIG_PATH
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def get(section, key, default=None, path=None):
    return load(path).get(section, {}).get(key, default)


def main(argv):
    if len(argv) not in (3, 4):
        sys.exit("usage: qg_config.py SECTION KEY [DEFAULT]")
    value = get(argv[1], argv[2], argv[3] if len(argv) == 4 else "", os.environ.get("QG_CONFIG"))
    print(" ".join(map(str, value)) if isinstance(value, list) else value)


if __name__ == "__main__":
    main(sys.argv)
