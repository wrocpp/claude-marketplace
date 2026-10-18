# Wro.cpp marketplace for Claude Code

Plugins that help Claude Code write C++ you would be happy to maintain. Each rule they teach is
backed by a fixture that compiles on the compilers it names, and each check that can be a script is
a script, so the advice does not depend on the model remembering it.

From [Wro.cpp](https://wrocpp.github.io), the Wrocław C++ community.

## Install

```bash
claude plugin marketplace add wrocpp/claude-marketplace
claude plugin install cpp26-guard@wrocpp
```

Inside a session the same thing is `/plugin marketplace add wrocpp/claude-marketplace`.

## Plugins

<!-- plugins:begin -->
| Plugin | Version | What it does | Install |
| --- | --- | --- | --- |
| [cpp26-guard](plugins/cpp26-guard) | 0.1.0 | Keep C++26 code free of hand-written copies of definitions: reflection instead of enum-to-string switches, name tables, flag chains and key/member blocks, with concepts, import std, format and print and a comment policy. | `claude plugin install cpp26-guard@wrocpp` |
| [cpp-quality-gates](plugins/cpp-quality-gates) | 0.1.0 | Make 'done' mean measured: a sanitizer matrix, a CRAP gate, mutation testing, coverage, compile-time undefined-behaviour checks and compiler capability tests, as skills with runnable scripts and CMake and CI templates. | `claude plugin install cpp-quality-gates@wrocpp` |
| [cpp-conventions](plugins/cpp-conventions) | 0.1.0 | Evidence-backed C++ conventions: designated initialisers, no needless copies, cppreference lookup, quantities as types and no magic numbers, each rule with compiler fixtures and an advisory pre-write scanner. | `claude plugin install cpp-conventions@wrocpp` |
| [cpp-modules](plugins/cpp-modules) | 0.1.0 | Use import std and named modules with CMake and GCC 16: the experimental gate, a working template project and the traps that cost hours, each reproduced by a fixture. | `claude plugin install cpp-modules@wrocpp` |
| [cpp-fuzzing](plugins/cpp-fuzzing) | 0.1.0 | Property-based and fuzz testing recipes for C++: one property function reused by AFL++ harnesses, corpus replay at compile time with #embed, bounded-exhaustive constexpr checks and compile-time undefined-behaviour detection. | `claude plugin install cpp-fuzzing@wrocpp` |
| [tidy-agent](https://github.com/wrocpp/tidy-agent/tree/main/plugins/tidy-agent) |  | Run clang-tidy on every C++ file the agent edits, and turn recurring agent mistakes into tested clang-tidy checks. | `claude plugin install tidy-agent@wrocpp` |
<!-- plugins:end -->

`tidy-agent` lives in its own repository and is listed here from there; the other plugins live in
[`plugins/`](plugins/).

## How the plugins behave

- **Advisory by default.** A hook adds a note for Claude; it never blocks an edit and it exits 0 on
  any internal error. A project opts in to blocking with `.claude/<plugin>.json`.
- **Self-contained.** A plugin installs alone: its scripts, fixtures and licence travel with it.
- **Measured.** A rule that depends on the compiler has a fixture and a result table in its skill;
  CI rebuilds the fixtures, so a compiler update shows up as a failing test.
- **Cheap to load.** Skills use progressive disclosure: a short `SKILL.md` and `references/` read on
  demand. `claude plugin details <name>` shows each plugin's projected token cost.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and [docs/plugin-conventions.md](docs/plugin-conventions.md).

## Licence

[MIT](LICENSE). Each plugin carries its own copy.
