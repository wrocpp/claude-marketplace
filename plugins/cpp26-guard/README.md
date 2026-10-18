# cpp26-guard

Keep C++26 code free of hand-written copies of definitions, and push Claude toward C++26 idioms. Reflection instead of enum-to-string switches, name tables, flag chains and key/member blocks; concepts instead of bare template parameters; `import std`, `std::format` and `std::print`; an opt-in comment policy. Two skills, a pre-write and a post-write advisory hook, two tested lints with allowance files, and a GCC 16.2 evidence table backed by compile probes.

Install: `/plugin install cpp26-guard --marketplace wrocpp/claude-marketplace`

## What it does

| Component | Purpose |
|---|---|
| Skill `reflect-dont-hand-write` | When Claude writes an enum-to-string mapping, a name lookup, a flag parser, a JSON field list or a handler table, it derives them with `std::meta` instead. Ships `references/reflect.hpp` (a small tested `enum_name`, `enum_from_name`, `enum_count`, annotation lookup, aggregate member walk and flag parser), `references/patterns.md` and `references/gcc-16.2-evidence.md` |
| Skill `cpp26-idioms` | Constrained templates, `import std`, `std::format`/`std::print`, one append instead of a chain, and the opt-in comment policy; `references/rules.md` lists what each rule sees and misses |
| PreToolUse hook | Scans the new text of an `Edit`, `Write` or `MultiEdit` on a C++ file and, when a rule fires, adds the finding and the replacement to Claude's context before the edit lands |
| PostToolUse hook | Scans the whole file after the edit and reports the same way |
| `scripts/reflection_lint.py`, `scripts/cpp26_lint.py` | The same scanners as command-line lints: `--strict` for CI, `--self-test`, explicit paths, an allowance file with `pending:` debt and stale-allowance failure |

Both hooks are advisory: they print `additionalContext`, always exit 0 and swallow every error (a malformed payload, config or allowance file never blocks an edit).

## Requirements

- Claude Code with plugin support; `python3` (standard library only; tested on 3.13 and 3.14); macOS or Linux.
- To use the reference header or the probes: GCC 16.2 or newer with `-std=c++26 -freflection`. The lints and hooks need no compiler.

## Rules

`reflection_lint` (skill `reflect-dont-hand-write`):

| Rule | Fires on | Known limits |
|---|---|---|
| `enum-name-switch` | three or more adjacent `case X::y: return "..."` arms (two of them returning a string), or a ternary chain `s == X::a ? "a" : s == X::b ? ...` | a switch that returns computed text; arms separated by other statements |
| `name-enum-table` | three or more adjacent `{"word", Type::member}` pairs | a table built with a helper call; it also fires on a table of wire words that differ from the enumerators on purpose (allow it) |
| `word-chain` | four or more `if (x == "literal")` lines within 12 lines of each other | a chain of unrelated string comparisons looks the same; a `switch` over a hash |
| `key-member-block` | three or more adjacent `{"key", x.key}` pairs whose key equals the member name | keys that differ from the member names |
| `json-format-template` | a string or raw string with three or more `"key":{}` placeholders | JSON assembled by concatenation |
| `enum-handler-table` | three or more adjacent `{Type::x, &fn}` pairs | tables built by `emplace` calls |
| `route-table` | three or more adjacent `{"GET", "/path", route::x}` rows | other row shapes |
| `enum-modulo` | `static_cast<Enum>(n % N)` with a literal or unnamed `N`, when the cast type is not arithmetic | the modulus hidden in a variable; a modulus spelled with `enum_count`, `enumerators_of` or `count_of` (or the configured `enum_count` helper) is accepted |
| `enum-word-list` | a `std::to_array<std::string_view>({...})` of three or more words that are a subset of one enum's enumerators | needs the enum in the scan: the CLI sees the whole scan, the hooks only the edited text |
| `stale-allowance` | an allowance line whose finding no longer exists | not judged for files outside the scanned paths |

`cpp26_lint` (skill `cpp26-idioms`):

| Rule | Default | Fires on | Known limits |
|---|---|---|---|
| `unconstrained-template` | on | `template <class T>` whose parameter is called, awaited, used as a stream or sink, or named like a role | a concept-in-name-only; a callable reached through a capture |
| `std-include` | on with `"modules": true` | a standard C++ header (not `<meta>`, `<contracts>`, C or POSIX headers) in a non-header file | includes that arrive through another header; header files are skipped |
| `legacy-io` | on | `<iostream>`, `std::cout`/`cerr`/`cin`, the `printf` family | wrappers and macros |
| `append-chain` | on | three or more `+=` or `push_back` statements in a row on one variable, in a non-constexpr function | appends in a loop |
| `string-temporary` | on | `std::string(1, c)` and `x += "lit" + a + b` | concatenation spread over statements |
| `comment` | off | any comment except `// Exception: <reason>` on its own line and a `}  // namespace x` closer | n/a |

The comment policy is the author's house style, not a general C++ recommendation: it is opt-in.

## Configuration

Everything is optional. Put `.claude/cpp26-guard.json` in the project:

```json
{
  "roots": ["src", "include", "tests"],
  "exclude": ["src/generated/"],
  "suffixes": [".cpp", ".cppm", ".hpp"],
  "modules": true,
  "allowance_file": ".claude/cpp26-guard-allow.txt",
  "rules": {"comment": true, "legacy-io": false},
  "helpers": {"enum_name": "reflect::enum_name", "enum_from_name": "reflect::enum_from_name"}
}
```

| Key | Default | Meaning |
|---|---|---|
| `roots` | `["src", "include", "app", "tests"]` | Directories (relative to the project root) the hooks and the lints cover |
| `exclude` | `[]` | Path prefixes skipped |
| `suffixes` | `.cpp .cc .cxx .cppm .ixx .hpp .hh .hxx .h .ipp` | File types scanned |
| `modules` | `false` | The project uses `import std`; switches `std-include` on |
| `allowance_file` | `.claude/cpp26-guard-allow.txt` | Where exceptions and debt are listed |
| `rules` | `{}` | `{"<rule>": true/false}` overrides the default for one rule |
| `helpers` | `{}` | Names the project's own helper in advice. Keys: `enum_name`, `enum_from_name`, `enum_count`, `enum_values`, `member_walk`, `append_all` |

An invalid config makes the lints exit with a message and the hooks stay silent.

### Untrusted input

The project's config, allowance file and source are untrusted, because the hooks run in whatever repository is open and their output becomes part of Claude's context. A helper value must be an identifier (`^[A-Za-z_][A-Za-z0-9_:<>]{0,63}$`) and `allowance_file` a relative path of at most 128 characters from `[A-Za-z0-9_./-]` without `..`; a value that fails is ignored, the default is used, and the output says only that a config value was ignored. Advice sentences are fixed plugin text. A finding quotes the matching line with comments and string contents blanked, control characters removed, at most 120 characters, labelled as quoted data; file names with unusual characters and allowance entries are never echoed. `tests/test_injection.py` checks this with instruction-shaped config values, paths, comments and file names.

### Allowance file

One line per exception: `path|rule|text fragment|reason`. A path ending in `/` covers a directory. A reason that starts `pending:` is debt to remove; the lints print the count (`allowances: 3 exceptions, 1 pending`). A line whose finding disappeared is reported as `stale-allowance`, which fails `--strict`.

```
src/http/status.cpp|name-enum-table|{"Not Found"|HTTP reason phrases are not enumerator names
src/old/log.cpp|legacy-io|std::cout|pending: move to std::println
```

### Command line

```bash
python3 "$CLAUDE_PLUGIN_ROOT/scripts/reflection_lint.py" --strict          # configured roots
python3 "$CLAUDE_PLUGIN_ROOT/scripts/cpp26_lint.py" --strict src/net       # explicit paths
python3 "$CLAUDE_PLUGIN_ROOT/scripts/cpp26_lint.py" --self-test
```

`--root DIR` selects the project (default: the current directory).

## Layout

```
.claude-plugin/plugin.json
hooks/hooks.json                  PreToolUse and PostToolUse on Edit|Write|MultiEdit
scripts/
  cpp_source.py                   tokeniser: comments, literals, raw strings, a code view and a skeleton view
  lint_common.py                  config, findings, allowances, stale detection, CLI
  reflection_lint.py              hand-written mirrors of definitions
  cpp26_lint.py                   C++26 idioms and the comment policy
  hook_common.py precheck.py postcheck.py
skills/
  reflect-dont-hand-write/        SKILL.md, references/{patterns.md, gcc-16.2-evidence.md, reflect.hpp}
  cpp26-idioms/                   SKILL.md, references/rules.md
tests/
  run.sh setup.sh                 the contract: exit 0 when everything passes
  test_*.py fixtures/             unit, hook payload, fixture and injection tests
  probes/{supported,absent}/      26 GCC 16.2 capability probes
  reference_selftest.cpp          builds and runs reflect.hpp
```

## Tests

```bash
sh tests/run.sh
```

It runs the Python unit tests, both lint self-tests, the hook payload tests (hand-written switch, bare called template, `#include <vector>` in a modules project, a stray comment under the comment policy, a clean snippet), compiles every probe with `g++-16 -std=c++26 -freflection -fsyntax-only` (probes in `absent/` must fail, and an internal compiler error does not count as a rejection) and builds and runs the reference header. Without GCC 16 it prints `SKIP g++-16`; with `WROCPP_CI=1` that skip is a failure. On Debian or Ubuntu, `sh tests/setup.sh` installs python3; use the `gcc:16` image for the compiler.

## Provenance

Adapted from the lints, hooks, skills and compiler probes of the author's own Apache-2.0 llmgate project, generalised (no project names or helpers, configuration through `.claude/cpp26-guard.json`) and relicensed MIT here.

MIT, see [LICENSE](LICENSE).
