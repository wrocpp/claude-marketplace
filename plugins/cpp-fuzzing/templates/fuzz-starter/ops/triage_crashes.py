#!/usr/bin/env python3
"""Copy AFL++ crashes and hangs into the regression corpus under a content-derived name.

    triage_crashes.py <findings-dir> <corpus-dir>

<findings-dir> is the afl-fuzz -o directory (it holds default/crashes and default/hangs, or one
such directory per fuzzer instance). A file is copied once: its name is the SHA-256 prefix of its
bytes, so running this twice, or on two machines, never duplicates. Nothing is executed and no name
from the findings directory is used in the destination path.
"""
import argparse
import hashlib
import pathlib
import shutil
import sys

KINDS = {"crashes": "crash", "hangs": "hang"}
NAME_LENGTH = 16
MAX_BYTES = 1 << 20


def candidates(findings):
    for kind in KINDS:
        for path in sorted(findings.glob(f"*/{kind}/id:*")):
            if path.is_file() and not path.is_symlink():
                yield kind, path


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("findings", type=pathlib.Path)
    parser.add_argument("corpus", type=pathlib.Path)
    args = parser.parse_args(argv)
    if not args.findings.is_dir():
        print(f"not a directory: {args.findings}", file=sys.stderr)
        return 2
    args.corpus.mkdir(parents=True, exist_ok=True)
    added = skipped = 0
    for kind, path in candidates(args.findings):
        size = path.stat().st_size
        if size > MAX_BYTES:
            print(f"skip {path.name}: {size} bytes is above {MAX_BYTES}")
            skipped += 1
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()[:NAME_LENGTH]
        target = args.corpus / f"{KINDS[kind]}-{digest}"
        if target.exists():
            continue
        shutil.copyfile(path, target)
        print(f"added {target.name} ({size} bytes)")
        added += 1
    print(f"{added} added, {skipped} skipped")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
