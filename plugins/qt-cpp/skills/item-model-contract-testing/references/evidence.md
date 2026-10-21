# Evidence: item-model-contract-testing

Runs: GCC 16.2.0 (`gcc:16`, Debian 13) with Qt 6.8.2 from `qt6-base-dev`, and GCC 16.2.0 with Qt 6.10.3
(`reflect-moc/gcc16-qt610`), both Linux aarch64, Debug build, `-Wall -Wextra -Werror`. Clang and MSVC were not run.

| fixture (`tests/cpp/`) | what it shows | Qt 6.8.2 | Qt 6.10.3 |
|---|---|---|---|
| `contract_correct_model.cpp` | the right model, 4 seeds of 4,000 steps (about 40 percent accepted, the rest refused or selections), tester Fatal, selection, persistent index, sorting proxy and its mirror: 0 mismatches, 0 violations | pass | pass |
| `contract_flaws_detected.cpp`, `forgot_end_insert` | `beginInsertRows` with no end: mirror reports "a change was announced and never confirmed" | caught | caught |
| `contract_flaws_detected.cpp`, `wrong_row_remove` | removal announced for the next row: the mirror shows another entry's value in row 1 | caught | caught |
| `contract_flaws_detected.cpp`, `silent_replace` | no `dataChanged`: caught by the mirror; with the mirror off the same run is clean, so no check on the model's own data sees it | caught, clean without mirror | caught, clean without mirror |
| `contract_flaws_detected.cpp`, `row_as_key` | the row answered for `Qt::UserRole`: 1,128 mismatches in the "no key role" check; with `stable_key_role = Qt::UserRole` the mirror reports the value shifting (key 0 cached, key 1 live) | caught | caught |

The right model passes the same driver in the same file, so a detection is not noise. The control runs stop at the
first violation; without that, a wrong adapter leaves Qt's bookkeeping unbalanced.

`QAbstractItemModelTester` printed "Trying to construct an instance of an invalid type, type id: 4097" to stderr on
Qt 6.8.2 in `contract_correct_model` and still passed; compare stdout only when diffing builds.
