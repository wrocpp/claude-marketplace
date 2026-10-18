#!/usr/bin/env python3
import json
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MARKETPLACE_NAME = "wrocpp"
LICENSE_ID = "MIT"
KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
FIELD = re.compile(r"^(\w[\w-]*):\s*(.*)$", re.MULTILINE)
REQUIRED_FILES = ("README.md", "LICENSE", "tests/run.sh")
EXECUTABLE_SUFFIXES = (".sh", ".py")
PLUGIN_ROOT = "${CLAUDE_PLUGIN_ROOT}/"
BARE_PLUGIN_PATH = re.compile(r"(?<![\w/.}$-])(?:scripts|templates)/[A-Za-z0-9_][A-Za-z0-9_./-]*")
ROOT_REFERENCE = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/([A-Za-z0-9_][A-Za-z0-9_./-]*)")
SKILL_DIR_WALK = re.compile(r"\$\{CLAUDE_SKILL_DIR\}/\.\.")


def fail(problems, message):
    problems.append(message)


def frontmatter_fields(text):
    block = FRONTMATTER.match(text)
    return {m.group(1): m.group(2) for m in FIELD.finditer(block.group(1))} if block else {}


def check_skill(problems, plugin, skill):
    fields = frontmatter_fields(skill.read_text(encoding="utf-8"))
    where = skill.relative_to(ROOT)
    if fields.get("name") != skill.parent.name:
        fail(problems, f"{where}: frontmatter name must equal the directory name {skill.parent.name!r}")
    if not fields.get("description"):
        fail(problems, f"{where}: frontmatter description is missing")


def check_skill_paths(problems, skill, plugin_dir):
    text = skill.read_text(encoding="utf-8")
    where = skill.relative_to(ROOT)
    for match in ROOT_REFERENCE.finditer(text):
        target = match.group(1).rstrip(".,;:")
        if not (plugin_dir / target).exists():
            line = text.count("\n", 0, match.start()) + 1
            fail(problems, f"{where}:{line}: ${{CLAUDE_PLUGIN_ROOT}}/{target} does not exist in the plugin")
    if SKILL_DIR_WALK.search(text):
        fail(problems, f"{where}: use ${{CLAUDE_PLUGIN_ROOT}}/..., not ${{CLAUDE_SKILL_DIR}}/.. (a path walk breaks if the skill moves)")
    for match in BARE_PLUGIN_PATH.finditer(text):
        before = text[max(0, match.start() - len(PLUGIN_ROOT)) : match.start()]
        if before != PLUGIN_ROOT:
            line = text.count("\n", 0, match.start()) + 1
            fail(problems, f"{where}:{line}: {match.group(0)!r} is a bare path; an installed plugin is not in the project, write ${{CLAUDE_PLUGIN_ROOT}}/{match.group(0)}")


def check_scripts(problems, directory):
    for path in directory.rglob("*"):
        if path.is_file() and path.suffix in EXECUTABLE_SUFFIXES and path.parent.name in ("hooks", "scripts", "tests") and not os.access(path, os.X_OK):
            fail(problems, f"{path.relative_to(ROOT)}: script is not executable")


def check_plugin(problems, entry):
    directory = ROOT / entry["source"]
    manifest_path = directory / ".claude-plugin" / "plugin.json"
    if not manifest_path.exists():
        return fail(problems, f"{entry['name']}: {manifest_path.relative_to(ROOT)} is missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for field in ("name", "version", "description", "license"):
        if not manifest.get(field):
            fail(problems, f"{entry['name']}: plugin.json has no {field}")
    if manifest.get("name") != entry["name"]:
        fail(problems, f"{entry['name']}: plugin.json name {manifest.get('name')!r} differs from the marketplace entry")
    if not SEMVER.match(manifest.get("version", "")):
        fail(problems, f"{entry['name']}: version {manifest.get('version')!r} is not semver")
    if manifest.get("license") != LICENSE_ID:
        fail(problems, f"{entry['name']}: license must be {LICENSE_ID}")
    for required in REQUIRED_FILES:
        if not (directory / required).exists():
            fail(problems, f"{entry['name']}: {required} is missing")
    for skill in sorted(directory.glob("skills/*/SKILL.md")):
        check_skill(problems, entry["name"], skill)
        check_skill_paths(problems, skill, directory)
    hooks = directory / "hooks" / "hooks.json"
    if hooks.exists():
        json.loads(hooks.read_text(encoding="utf-8"))
    check_scripts(problems, directory)


def main():
    problems = []
    data = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    if data.get("name") != MARKETPLACE_NAME:
        fail(problems, f"marketplace name must be {MARKETPLACE_NAME!r}")
    names = [entry["name"] for entry in data["plugins"]]
    if len(set(names)) != len(names):
        fail(problems, "duplicate plugin names")
    for entry in data["plugins"]:
        if not KEBAB.match(entry["name"]):
            fail(problems, f"{entry['name']}: name must be kebab-case")
        if isinstance(entry["source"], str):
            check_plugin(problems, entry)
    for problem in problems:
        print(problem)
    print(f"{len(data['plugins'])} plugins, {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
