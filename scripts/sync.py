#!/usr/bin/env python3
import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
README = ROOT / "README.md"
TABLE_BEGIN = "<!-- plugins:begin -->"
TABLE_END = "<!-- plugins:end -->"
ENTRY_FIELDS = ("name", "source", "description", "version", "author", "license", "keywords")
MANIFEST_FIELDS = ("description", "version", "author", "license", "keywords")
INDENT = 2


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(data):
    return json.dumps(data, indent=INDENT, ensure_ascii=False) + "\n"


def synced_entry(entry):
    source = entry["source"]
    if not isinstance(source, str):
        return entry
    manifest = load(ROOT / source / ".claude-plugin" / "plugin.json")
    merged = {"name": manifest["name"], "source": source}
    merged.update({field: manifest[field] for field in MANIFEST_FIELDS if field in manifest})
    return {field: merged[field] for field in ENTRY_FIELDS if field in merged} | {k: v for k, v in entry.items() if k not in ENTRY_FIELDS}


def synced_marketplace(data):
    updated = dict(data)
    updated["plugins"] = [synced_entry(entry) for entry in data["plugins"]]
    return updated


def first_sentence(text):
    end = text.find(". ")
    return (text if end < 0 else text[: end + 1]).strip()


def table(data):
    rows = ["| Plugin | Version | What it does | Install |", "| --- | --- | --- | --- |"]
    for entry in data["plugins"]:
        install = f"`claude plugin install {entry['name']}@{data['name']}`"
        rows.append(f"| [{entry['name']}]({link(entry)}) | {entry.get('version', '')} | {first_sentence(entry['description'])} | {install} |")
    return "\n".join(rows)


def link(entry):
    source = entry["source"]
    if isinstance(source, str):
        return source.removeprefix("./")
    return f"https://github.com/{source['url']}/tree/main/{source.get('path', '')}".rstrip("/")


def synced_readme(data):
    text = README.read_text(encoding="utf-8")
    head, rest = text.split(TABLE_BEGIN, 1)
    _, tail = rest.split(TABLE_END, 1)
    return f"{head}{TABLE_BEGIN}\n{table(data)}\n{TABLE_END}{tail}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    current = load(MARKETPLACE)
    wanted = synced_marketplace(current)
    outputs = {MARKETPLACE: dump(wanted), README: synced_readme(wanted)}
    stale = [path for path, text in outputs.items() if path.read_text(encoding="utf-8") != text]
    if args.check:
        for path in stale:
            print(f"out of date: {path.relative_to(ROOT)} (run scripts/sync.py)")
        return 1 if stale else 0
    for path in stale:
        path.write_text(outputs[path], encoding="utf-8")
        print(f"updated {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
