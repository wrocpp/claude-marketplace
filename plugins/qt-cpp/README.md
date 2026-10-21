# qt-cpp

Qt item models written in C++: how to test them through a view's eyes, how to wire a container to a model once, the
build traps that cost hours, and a text lint with an advisory hook that catches four of the mistakes while Claude
writes. Every rule is backed by a fixture, and the skills say which Qt and compiler it was run with.

Install: `claude plugin marketplace add wrocpp/claude-marketplace && claude plugin install qt-cpp@wrocpp`

Written with Claude Code; every rule is backed by a fixture that was run.

## What you get

| skill | what it prevents |
|---|---|
| `item-model-contract-testing` | A model that passes a check on its own data and still shows ghost rows: a `beginInsertRows` with no end, a removal announced for the wrong row, a value changed with no `dataChanged`, a row used as a key. A view mirror built from signals only, a seeded random driver against a plain reference, `QAbstractItemModelTester` in Fatal mode, selection and persistent-index survival, a sorting proxy with a second mirror, and wrong adapters as controls. |
| `container-to-model-patterns` | Hand-written begin/end wiring per model, a row found by walking the container, a key role that shifts under every insert, a range announced row by row, an edit that bypasses the container, a model in another thread, a value whose move can throw. |
| `qt-build-traps` | An unqualified `connect` in a class template that calls the wrong function silently, `slots` and `signals` as macros, template commas in a test macro, a class name Qt does not normalize (abort on registration), a two-file test that proves nothing without `-flto -Wodr`, `Q_OBJECT` in a template, test-tool noise on stderr, ninja dyndep assertions. |
| `qml-types-from-cpp` | Thin: registering a C++ type, handler argument names, a property binding, an object and a model as context properties. Only what a headless fixture ran. |

## The lint and the hook

`scripts/qt_model_lint.py` reads C++ text (comments and strings blanked) and reports four rules:

| rule | finds |
|---|---|
| `begin-end-pairing` | a `begin{Insert,Remove,Move}{Rows,Columns}` or `beginResetModel` call with no matching `end*` in the same function (a lambda counts as part of the function that holds it) |
| `dependent-base-connect` | an unqualified `connect(` inside a class template whose base list names a template parameter |
| `row-as-key` | a `data()` override that answers a role named like a key (`KeyRole`, `IdRole`, ...) with the row |
| `fromvalue-in-template-emit` | `QVariant::fromValue(` inside an `emit` in a template |

```bash
python3 scripts/qt_model_lint.py src/          # files or directories; exit 1 when there is a finding
```

The `PostToolUse` hook (`hooks/lint_hook.py`) runs the lint on every C++ file Claude writes or edits and adds the
findings as context. It reads the file as it is on disk, because a begin and its end can be far apart. Configuration, in
the project's `.claude/qt-cpp.json` (all optional):

```json
{"row-as-key": {"block": true}, "fromvalue-in-template-emit": {"disable": true}}
```

Advisory by default: exit 0, never blocks. `"block": true` for a rule makes it report to stderr with exit 2. A finding is
silenced on its line or the line before with `// qt-model-ok: <reason>`; the reason is required. `QT_CPP_OFF=1` switches the
hook off. The hook never fails an edit: any error in it exits 0.

The lint reads text, not types. A begin in one slot and its end in the paired slot is reported (mark it with the
marker); a conditional early return between a begin and its end is not; the dependent-base rule does not see
out-of-class member definitions of a class template.

The hook treats the repository as untrusted. Only booleans are read from the config, under a fixed vocabulary of rule
names; a config that cannot be read keeps the defaults and the report adds one fixed sentence. Source is read with comments
and strings blanked, and none of its text is echoed: a finding is the rule id, the line number and a fixed sentence
from the plugin. A file name is shown only if
it is plain. The hook starts no process, so no config value can reach a command line. `tests/test_untrusted.py` feeds
instruction-shaped source, config and file names and asserts none of that text appears in the output.

## Requirements

- `python3` (standard library only) for the lint and the hook.
- To run the fixtures: a C++20 compiler, CMake 3.21 and Qt 6 with Core, Test and (for the QML fixture) Qml and moc.
  On Debian or Ubuntu: `qt6-base-dev qt6-base-dev-tools qt6-declarative-dev` (`tests/setup.sh` installs them with cmake
  and ninja). The helpers in `include/qt_cpp/` need only Qt Core and, for the driver, Qt Test.
- Optional fixtures: GCC 16.2 or newer, Qt 6.10 and a checkout of [reflect-moc](https://github.com/wrocpp/reflect-moc)
  (`REFLECT_MOC_DIR`). Without them the runner prints `SKIP reflect-moc fixtures (...)`, in CI too.

## Layout

```
include/qt_cpp/model_contract.hpp   ModelWatcher + the random driver (run_random) for a list model
include/qt_cpp/row_index.hpp        IdentityIndex, SortedIndex, InsertionOrderIndex (LiveSlots), the Multi indexes
scripts/qt_model_lint.py            the lint        scripts/cpp_text.py   masking and config helpers
hooks/lint_hook.py                  the PostToolUse hook
skills/*/SKILL.md                   the four skills, with references/evidence.md each
tests/cpp/                          Qt fixtures: list model, wrong adapters, contract runs, row index, traps, QML
tests/cpp/reject, tests/cpp/accept  must not build / must build: pairs
tests/lint-fixtures/                one file per rule, each flagged line marked `// FINDING <rule>`
tests/optional/                     reflect-moc fixtures
```

## Tests

```bash
sh plugins/qt-cpp/tests/run.sh
```

- `tests/test_lint.py`: the lint in both directions (every `FINDING` line is reported and nothing else), the masking,
  the command line, the plugin's own code, and a complexity limit of 8 per function.
- `tests/test_untrusted.py`: hook output from hostile config, source and file names; blocking, disabling, silence.
- `tests/CMakeLists.txt` (AUTOMOC, Debug): the contract runs, the row indexes, the thread assertion, the build traps and
  the QML fixture, run with `ctest`; then `tests/check_reject.py` builds each reject fixture and checks it fails with the
  text on its first line (`// expect-error: <regex>`).
- `tests/optional/run.sh`: the reflect-moc fixtures.
- `WROCPP_CI=1`: a missing cmake or Qt 6 fails instead of printing `SKIP`. Docker on a Mac:
  `docker run --rm -v "$PWD":/src -w /src -e WROCPP_CI=1 gcc:16 sh -c 'sh plugins/qt-cpp/tests/setup.sh && sh plugins/qt-cpp/tests/run.sh'`.

## What the evidence does not cover

- **Compilers and Qt.** GCC 16.2.0 only, with Qt 6.8.2 (Debian 13 packages) and Qt 6.10.3, on Linux aarch64 (and x86_64 in
  the marketplace CI). No Clang, no MSVC, no macOS or Windows build, no Qt 5. The messages the reject fixtures match are GCC's.
- **Models.** The driver is list-shaped (one column, no children). Table and tree models, delegates, threads and a model with
  no source object are not driven. A keyed model (map, hash, set, multi) over the row indexes has no fixture here.
- **Speed.** The row index speedup is measured in reflect-moc, not re-run here.
- **Environment traps.** The `QAbstractItemModelTester` stderr line was seen; the ninja dyndep assertion and the
  branch-switch hazard come from reflect-moc's docker runs and have no fixture.
- **The lint** reads text. It cannot see a conditional path between a begin and its end, a connect that reaches the
  right function by luck, or a key role named something else.
- **QML.** Qt Quick items, views and `qt_add_qml_module` are not exercised.

## Background

Not dependencies, only where the evidence came from: the [reflect-moc](https://github.com/wrocpp/reflect-moc)
repository (observable containers and their models, with fixtures for every container), and two wro.cpp posts,
[typed signals in a class template, without moc](https://wrocpp.github.io/posts/qt-class-template-typed-signals-without-moc/)
and [observable models: known limits](https://wrocpp.github.io/posts/qt-observable-models-known-limits/) (live from
28 October 2026).
