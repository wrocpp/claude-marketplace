# Evidence: container-to-model-patterns

Runs as in the contract skill: GCC 16.2.0, Qt 6.8.2 and Qt 6.10.3, Linux aarch64, Debug build. Clang not run.

| fixture (`tests/cpp/`) | what it shows | Qt 6.8.2 | Qt 6.10.3 |
|---|---|---|---|
| `row_index.cpp`, insertion-order | 30,000 random inserts and removals over 700 keys with drains that leave more than half the slots dead: `keyAt` and `rowOf` agree with a plain vector throughout | pass | pass |
| `row_index.cpp`, compaction | after 390 of 400 removals `keyAt` still answers; `LiveSlots::needs_compaction` is true above 64 slots with under half live | pass | pass |
| `row_index.cpp`, sorted, multi sorted, multi insertion | same, against a plain vector (multi: 12 keys, occurrence 0 newest) | pass | pass |
| `list_ranges_and_edits.cpp`, range | `insertRange` of 5 and `removeRange` of 3 each send one `rowsAboutToBe*` and one `rows*` | pass | pass |
| `list_ranges_and_edits.cpp`, edit | `setData` goes through `replace`: one `dataChanged`; a non-number, a bad row and a non-edit role change nothing | pass | pass |
| `list_ranges_and_edits.cpp`, one thread | a model made in another thread than its source dies of SIGABRT in a Debug build; the same thread does not | pass | pass |
| `reject/throwing_move.cpp` | a value type whose move can throw fails with "the value type must be nothrow move constructible and assignable"; a noexcept move compiles | rejected | rejected |

Not re-run here: the speedup of a row index over a linear walk (reflect-moc `docs/measurements.md`: 16 to 40 microseconds
per change at 100,000 hash entries and 10,000 map entries before, a few hundred nanoseconds after; the ratio depends on
the machine and is quoted there as 49 to 211 times on one and 42 to 125 times on another).
