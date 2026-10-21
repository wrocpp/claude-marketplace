# Evidence: qt-build-traps

GCC 16.2.0 with Qt 6.8.2 (`gcc:16`, Debian 13) and with Qt 6.10.3 (`reflect-moc/gcc16-qt610`), Linux aarch64, Debug
build. A reject fixture must fail to build with the text in its first line; its control must build. Clang and MSVC
were not run, and their messages differ.

| fixture (`tests/cpp/`) | result on both Qt versions |
|---|---|
| `traps/dependent_base_connect.cpp` | unqualified `connect` in `Unqualified<QObject>` called the decoy in the sender's namespace (1 call) and connected nothing (0 hits); `QObject::connect` and `this->connect` connected (1 hit each) and did not touch the decoy |
| `reject/slots_is_a_macro.cpp` | `error: expected unqualified-id before ')' token` |
| `reject/qt_no_keywords_removes_signals.cpp` | `error: 'signals' does not name a type` |
| `accept/slots_renamed_and_q_keywords.cpp` | builds (control of the two above) |
| `reject/template_commas_in_check_macro.cpp` | `error: macro 'CHECK' passed 2 arguments, but takes just 1` |
| `accept/check_macro_parens.cpp` | builds (control) |
| `traps/normalized_names.cpp` | 14 spellings: `QMetaObject::normalizedType` gives Qt's form (`unsigned int` to `uint`, `> >` to `>>`, no space after a comma); `qRegisterNormalizedMetaType<T*>("A<uint>*")` runs, `"A<unsigned int>*"` and `"A<B<int> >*"` die of SIGABRT in a Debug build |
| `reject/odr_violation/` | `-flto -Wodr -Werror`: `error: type 'struct Row' violates the C++ One Definition Rule`; `odr/` (same flags, agreeing units) links and runs |
| `reject/q_object_in_template_by_moc.cpp` | moc itself refuses: `error: Template classes not supported by Q_OBJECT`; the workaround builds and passes: signals in `ListSignals`, the template `ObservableList<T>` derived from it, a `ListModelBase` template with no `Q_OBJECT` used as a `QAbstractListModel` (`contract_correct_model`) |
| `optional/reflect_moc_two_tus_a.cpp` | with reflect-moc main 95902b4: one specialization of a class template with typed signals in two units, same flags: meta-object, signal index and signal member type name agree; links and runs (Qt 6.10.3 only) |
| `optional/reflect_moc_class_template_normalized.cpp` | with reflect-moc: class names of `Keyed<unsigned>` and `Keyed<QList<unsigned char>>` are `uint` and `uchar` forms, and `QVariant::fromValue(ptr)` round-trips (Qt 6.10.3 only) |

Not covered: a class name for a specialization over `unsigned short`, `unsigned long` or `long long`. With reflect-moc
main 95902b4 on GCC 16.2 those came out as `short uint`, `long uint` and `qlonglong int`, which Qt's normalizer leaves alone
but are not Qt's own `ushort`, `ulong` and `qlonglong`; no fixture pins that, because it looks like a reflect-moc defect
and not a rule.
