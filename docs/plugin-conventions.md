# Plugin conventions

What every plugin in this marketplace follows. `scripts/validate.py` checks the mechanical parts.

## Layout

```
plugins/<name>/
  .claude-plugin/plugin.json   name, version, description, author, license, keywords, repository
  README.md                    what it does, the install line, requirements, layout
  LICENSE                      MIT, a copy per plugin
  skills/<skill>/SKILL.md      short; detail in references/
  hooks/hooks.json + *.py      advisory hooks
  scripts/                     runnable helpers
  tests/run.sh                 exit 0 when every test and fixture passes
  tests/setup.sh               optional: install the test dependencies on Debian or Ubuntu
```

- The directory name, the `plugin.json` name and the marketplace entry name are the same.
- A plugin is self-contained: nothing outside its directory is read (paths with `..` are rejected
  by Claude Code). A small helper shared by two plugins is copied, not linked.
- `marketplace.json` entries for in-repo plugins are generated from each `plugin.json` by
  `scripts/sync.py`. Edit the manifest, never the entry.

## README

Every plugin README has the line that installs it from this marketplace, because the plugin is also read on its own:

```
/plugin install <name> --marketplace wrocpp/claude-marketplace
```

## Skills

- The frontmatter `name` equals the directory name. The `description` says when to load the skill
  and lists trigger phrases; it is what decides whether the skill loads.
- One fact lives in one place. A skill links to the canonical one instead of restating it.
- A rule that depends on a compiler or library carries an evidence table: the fixture, the
  compilers and versions, and what each did.

## Hooks

- Advisory by default: print `{"hookSpecificOutput": {"hookEventName": ..., "additionalContext": ...}}`
  and exit 0. A broken hook must never break an edit: catch everything and exit 0.
- A hook that can block does so only when the project's `.claude/<plugin>.json` says
  `{"<rule>": {"block": true}}`; the report goes to stderr with exit 2.
- Scanners read text, not compiler state: the compiler may not support what the project uses.

## Tests

- `tests/run.sh` is the contract CI uses. It prints what it ran and exits non-zero on failure.
- Fixtures are small `.cpp` files named by behaviour. Each says which compilers must accept it and
  which must reject it; the runner checks both directions.
- A compiler that is not installed is reported as `SKIP <compiler>`; CI installs the ones it needs
  so a skip there is a failure.

## Versioning and release

Semver. Before 1.0 a breaking change is a minor bump. A release is a commit that bumps
`plugin.json`, followed by `python3 scripts/sync.py` so the marketplace entry and README follow.
CI fails when they are out of step.

## Licence and provenance

MIT, copyright "Wro.cpp contributors". Do not add text copied from sources whose licence forbids it:
cite the page (cppreference, a standard paper, a compiler bug) and write the explanation yourself.
