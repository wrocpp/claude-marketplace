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
| [cpp26-guard](plugins/cpp26-guard) | 0.1.0 | Keep C++26 free of hand-written copies of definitions. | `claude plugin install cpp26-guard@wrocpp` |
| [cpp-quality-gates](plugins/cpp-quality-gates) | 0.1.0 | Make 'done' mean measured for C++: skills for a sanitizer matrix (ASan, UBSan, TSan, LSan; Linux-in-a-container for macOS), a CRAP gate (lizard + gcovr), mutation testing (universalmutator harness with triage), and a compiler capability matrix, with runnable scripts, CMake presets and CI templates. | `claude plugin install cpp-quality-gates@wrocpp` |
| [cpp-conventions](plugins/cpp-conventions) | 0.1.0 | Evidence-backed C++ conventions as five skills - designated-init (one braced expression per value), no-needless-copies (views, sinks, ownership boundaries), cppreference (confirm a rule and cite the page, cached offline), units (std::chrono and mp-units quantities, one wall clock) and no-magic-numbers (name every number once) - with compiler fixtures for GCC and Clang and an advisory pre-write hook that scans new C++ text for copy smells and bare numbers. | `claude plugin install cpp-conventions@wrocpp` |
| [cpp-modules](plugins/cpp-modules) | 0.1.0 | Use import std and named modules with CMake and GCC 16: the experimental gate, a working template project and the traps that cost hours, each reproduced by a fixture. | `claude plugin install cpp-modules@wrocpp` |
| [cpp-fuzzing](plugins/cpp-fuzzing) | 0.1.0 | One property function reused by every kind of C++ check, as three skills and a working starter: one-property-many-checks (unit tests, AFL++ and compile-time undefined-behaviour checks share one constexpr property), compile-time-corpus-and-exhaustive (#embed corpus replay and bounded-exhaustive static_asserts with budget and memory guidance), afl-harness (replay-and-AFL++ harness, Docker recipe, time-boxed campaign, crash triage). | `claude plugin install cpp-fuzzing@wrocpp` |
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
