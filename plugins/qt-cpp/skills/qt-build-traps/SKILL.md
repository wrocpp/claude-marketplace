---
name: qt-build-traps
description: Use when a Qt C++ build or test fails in a way the message does not explain, or before writing a class template that derives from a Qt class, uses signals or connect, or is registered as a metatype. Covers an unqualified connect in a class template with a dependent base, `slots` and `signals` as macros and QT_NO_KEYWORDS, template commas in a CHECK macro, class names of template specializations that Qt does not normalize (qRegisterNormalizedMetaType aborts), a two-translation-unit test with -flto -Wodr, Q_OBJECT in a class template, QAbstractItemModelTester stderr noise, and ninja dyndep assertions when two builds touch one build tree. Trigger phrases - "connect not found", "expected unqualified-id", "slots", "QT_NO_KEYWORDS", "not normalized type name", "qRegisterNormalizedMetaType", "Q_OBJECT in a template", "moc template", "One Definition Rule", "-Wodr", "RefreshDyndepDependents", "macro passed 2 arguments".
---

# Qt build traps

Each trap below was hit, reproduced by a fixture that fails (or passes) on purpose, and has a control that compiles.
Fixtures live in `${CLAUDE_PLUGIN_ROOT}/tests/cpp`; the evidence table is in [evidence](references/evidence.md).

| trap | do this | fixture |
|---|---|---|
| In a class template whose base is a template parameter, unqualified `connect(...)` is not looked up in the base. Only argument-dependent lookup is left, so any function named `connect` in a namespace of an argument is called instead, and nothing is connected, with no diagnostic. | Write `QObject::connect(...)` or `this->connect(...)`. | `traps/dependent_base_connect.cpp` |
| `slots` and `signals` are macros once a Qt header is included: `int slots()` or a variable called `slots` fails with "expected unqualified-id". | Rename it, or define `QT_NO_KEYWORDS` and write `Q_SLOTS` / `Q_SIGNALS`. | `reject/slots_is_a_macro.cpp` |
| With `QT_NO_KEYWORDS`, `signals:` and `emit` stop existing, so a header that copies the define from another file and still uses them breaks. | Use `Q_SIGNALS` and `Q_EMIT` in any header that may see the define. | `reject/qt_no_keywords_removes_signals.cpp`, control `accept/slots_renamed_and_q_keywords.cpp` |
| A macro argument is split at every comma outside parentheses: `CHECK(f<QMap<int, S>>("x"))` is two arguments. | One more pair of parentheses: `CHECK((f<QMap<int, S>>("x")))`. | `reject/template_commas_in_check_macro.cpp`, control `accept/check_macro_parens.cpp` |
| Qt registers a pointer to a class under `className() + "*"` and, in a debug build, aborts on a name it would normalize differently. A compiler spells a specialization its own way (GCC: `unsigned int`, `> >`, a space after a comma); Qt wants `uint`, `>>` and none. This bites `QVariant::fromValue(ptr)`, `qmlRegisterType` and a pointer as a signal argument. | Build any class or metatype name by hand through `QMetaObject::normalizedType` and compare. A hand-written normalizer is checked against it on many spellings. | `traps/normalized_names.cpp` |
| A test of a class-template specialization used from two files proves nothing without the right flags: the second definition silently wins. | Link with `-flto -Wodr -Wlto-type-mismatch -Werror` and assert the meta-object, a signal's method index and the signal member's type name agree across the units. | `reject/odr_violation/`, control `odr/`; with a template of typed signals: `optional/reflect_moc_two_tus_a.cpp` |
| moc rejects `Q_OBJECT` in a class template. A model that is not `Q_OBJECT` still works as a `QAbstractListModel` subclass (it has no signals or slots of its own). | Put the signals in a non-template base and derive the template from it, or give the template no signals. | `reject/q_object_in_template_by_moc.cpp`; the workaround in `list_signals.hpp`, `observable_list.hpp`, `list_model.hpp` |

## Environment traps (observed, no fixture)

- **`QAbstractItemModelTester` prints "Trying to construct an instance of an invalid type, type id: 4097" to stderr**
  in some builds (seen with Qt 6.8.2 in `contract_correct_model`). When you diff the output of two builds, diff
  stdout only.
- **ninja's dyndep step (CMake C++ modules mode) asserts `Plan::RefreshDyndepDependents`** when two builds touch one
  build tree at once or a build is interrupted. Delete the build directory and rebuild with fewer jobs. Never run two
  builds on one tree.
- **Never switch git branches under a running container build that mounts the tree**: the sources change mid-build.
  One worktree per branch and per session.

These two are from reflect-moc CI and docker runs; this plugin has no fixture for them.

## The lint

`${CLAUDE_PLUGIN_ROOT}/scripts/qt_model_lint.py` finds the first and the `QVariant::fromValue` at an emit in a template
(the boxing that needs a normalized name), plus begin/end pairing and a row used as a key. The hook runs it after every
edit of a C++ file and only adds context. See the plugin README for the config.
