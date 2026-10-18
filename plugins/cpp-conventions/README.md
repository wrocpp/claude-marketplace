# cpp-conventions

Evidence-backed C++ conventions as skills, plus an advisory scanner that looks at the C++ text Claude is about to write. Every rule that depends on a compiler is backed by a fixture compiled with GCC and Clang, and the results are in the skill.

Install: `/plugin install cpp-conventions --marketplace wrocpp/claude-marketplace`

## What you get

| skill | rule in one line |
|---|---|
| `designated-init` | State a value's whole contents in one braced expression: designated initializer for an aggregate, initializer list for a container; never default-construct then assign or `push_back`. Knows which compiler stays silent about an omitted member. |
| `no-needless-copies` | Borrow with a view, transfer with a move, share `shared_ptr<const T>`, return by value; copy only at an ownership boundary you can name. Knows which compiler diagnoses a dangling view (GCC 16 does not). |
| `cppreference` | Confirm a language or library rule on cppreference.com before asserting it, and return the page and anchor to cite. Caches pages; works offline from the cache. |
| `units` | Quantities carry their unit in the type (`std::chrono`, mp-units); one wall clock; how to define a new unit or dimension. |
| `no-magic-numbers` | Name every number once, with its source beside it; only 0, 1 and 100% stand bare; a guard test keeps it so. |

The `PreToolUse` hook (`hooks/pre_write_scan.py`) runs two scanners over the new text of every `Write`, `Edit` and `MultiEdit` of a C++ file and passes the findings to Claude as context:

- `scripts/copy_scan.py` - copy smells (`const std::string&` parameters, sinks stored by copy, range-for copies, `substr`, `return std::move(local)`, views of temporaries, `[&]` captures into threads).
- `scripts/number_scan.py` - bare numbers (everything except 0, 1, 100% and the documented exemptions).

Both are also command-line guard tests: `python3 scripts/number_scan.py --check src/`.

Configuration, in the project's `.claude/cpp-conventions.json` (all optional):

```json
{
  "copies": {"block": false, "disable": false},
  "numbers": {"block": false, "disable": false, "allow": [2, 8]}
}
```

Advisory by default. `"block": true` makes that scanner stop the write (stderr, exit 2). A finding is silenced on the line with `// copy-ok: <ownership boundary>` or `// magic-ok: <where the number comes from>`; the reason is required. `CPP_CONVENTIONS_OFF=1` switches the hook off. The hook never fails an edit: any error in it exits 0.

Pairs with the separate `tidy-agent` plugin, which runs clang-tidy on every edit. This plugin does not run clang-tidy and does not duplicate that hook: the scanners read text, clang-tidy reads types.

## Requirements

- `python3` (standard library only; tested with 3.13 and 3.14) for the hook, scanners and the cppreference helper.
- Network access is optional: `cppreference` fetches an uncached page once; with `--offline` or `WROCPP_OFFLINE=1` it uses the cache only (`WROCPP_CACHE_DIR`, default `~/.cache/wrocpp`).
- To run the tests: a C++ compiler. GCC 14+ and Clang 18+ with `-std=c++23` are exercised; `-std=c++2c` for two fixtures.

## Tests

```bash
sh plugins/cpp-conventions/tests/run.sh
```

- `tests/test_scripts.py` - scanner unit tests, the cppreference helper against a bundled cache, and the hook probe payloads in `tests/hook-probes/`. No network.
- `tests/check_fixtures.py` - compiles every `tests/fixtures/*.cpp` with every compiler found (GCC, Clang, Apple clang) and compares with `tests/fixtures/expectations.json` in both directions; prints a results table. A compiler that is not installed prints `SKIP <family>`; with `WROCPP_CI=1` it fails instead. `WROCPP_COMPILERS="g++-16 clang++"` chooses the compilers.
- `tests/optional/` - mp-units fixtures, run when `MP_UNITS_DIR` points at a v2.x checkout or `WROCPP_NETWORK=1` lets the runner clone the pinned tag.
- `tests/setup.sh` installs the Debian/Ubuntu dependencies (for the `gcc:16` image).

## Layout

```
.claude-plugin/plugin.json
hooks/hooks.json, hooks/pre_write_scan.py
scripts/copy_scan.py, number_scan.py, cpp_text.py
skills/
  designated-init/        SKILL.md, references/{patterns,evidence}.md
  no-needless-copies/     SKILL.md, references/{scanner,evidence}.md
  cppreference/           SKILL.md, scripts/cppreference.py
  units/                  SKILL.md, references/mp-units.md
  no-magic-numbers/       SKILL.md, references/scanner.md
tests/                    run.sh, setup.sh, check_fixtures.py, test_scripts.py,
                          fixtures/, hook-probes/, optional/
```

Licence: MIT. The text, scanners and fixtures are original; rules cite public references (cppreference.com, the C++ standard, compiler documentation) rather than copying them.
