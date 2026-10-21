---
name: container-to-model-patterns
description: Use when exposing a container (QList, QMap, QHash, QSet, QMultiMap, QMultiHash, std::vector) as a Qt item model, or when a model's insert, remove or replace gets slower as the container grows. Pairs begin and end calls once in one generic base, finds a row from a key and a key from a row with a row index instead of walking the container, announces a range as one change, edits through the container, and keeps a model in its container's thread. Trigger phrases - "container model", "wrap a QList in a model", "QHash as a model", "QMap model", "row of a key", "key of a row", "model is slow with many entries", "beginMoveRows", "setData replace", "model thread", "nothrow move", "observable container".
---

# Container to model patterns

Write the wiring between a container and its models **once**, in a base, and give the base a row index. A concrete
model then supplies `data()` and nothing else.

## Patterns

1. **Begin and end, once.** The container announces `aboutToInsert/inserted`, `aboutToRemove/removed`,
   `changed`, `aboutToMove/moved`, `aboutToClear/cleared`. One base connects each pair to `beginInsertRows` /
   `endInsertRows` and the others. See `${CLAUDE_PLUGIN_ROOT}/tests/cpp/list_model.hpp`. Contract-test the base
   ([item-model-contract-testing](../item-model-contract-testing/SKILL.md)); a hand-written adapter per model is
   where a missing `endInsertRows` comes from.
2. **A row index per container order**, behind the same calls (`rowToInsert`, `rowOf`, `keyAt`, `insert`, `erase`),
   so the model has no branch on the container. `${CLAUDE_PLUGIN_ROOT}/include/qt_cpp/row_index.hpp`:

   | container | index | cost |
   |---|---|---|
   | list | `IdentityIndex`: the key is the row | none |
   | sorted (`QMap`, `QSet` sorted) | `SortedIndex`: a sorted vector of keys, binary search | O(log n) + a memmove |
   | unordered (`QHash`, `QSet`) | `InsertionOrderIndex`: a Fenwick tree over insertion slots, dead slots left by a removal, rebuilt when over half are dead | O(log n) |
   | `QMultiMap`, `QMultiHash` | `MultiSortedIndex`, `MultiInsertionIndex` over `MultiKey{key, occurrence}` | as above |

   A model that finds a row by walking the container costs time linear in the entries (a `QMap` counts a row by
   walking its tree). Measured in reflect-moc, not re-run here: 16 to 40 microseconds per change at 100,000 hash
   entries and 10,000 map entries, and the index made it dozens to hundreds of times cheaper (reflect-moc
   `docs/measurements.md`; two machines gave 49 to 211 and 42 to 125 times). Test the index against a plain vector
   across compaction: `${CLAUDE_PLUGIN_ROOT}/tests/cpp/row_index.cpp`.
3. **No key role for rows that shift.** A list's key is its row, and a multi container's `(key, occurrence)` shifts
   too, both with no signal, so a sorting proxy that caches the role goes stale. Offer a key role only for a map,
   hash or set. In a multi container an entry is `(key, occurrence)`, occurrence 0 the most recently inserted; an
   insert that names another occurrence is refused.
4. **A range is one change.** `insertRange` / `removeRange` for a list announce `[first, last]` once: one begin and
   one end however long the run. Only a list has contiguous positions; refuse the rest.
5. **Edit through the container.** `setData` builds the new value and calls the container's `replace`; the change is
   announced like any other, a refused edit changes nothing, and a column with no editor is not `ItemIsEditable`.
   One `dataChanged(index(row, 0), index(row, last))` covers every column of the row.
6. **One thread.** A container and its models live in one thread, so the connections are direct. Assert it in the
   base (`Q_ASSERT_X(source->thread() == this->thread(), ...)`) and test the assertion in a child process
   (`fork()`, expect SIGABRT): `${CLAUDE_PLUGIN_ROOT}/tests/cpp/list_ranges_and_edits.cpp`.
7. **Nothrow move.** A Qt container allocates inside the insert, so nothing can be prepared before the "about" signal
   and a throw cannot be undone. Refuse what can be refused at compile time:
   `static_assert(std::is_nothrow_move_constructible_v<T> && std::is_nothrow_move_assignable_v<T>)`, and a
   compile-fail fixture (`${CLAUDE_PLUGIN_ROOT}/tests/cpp/reject/throwing_move.cpp`).

The base is a class template with a dependent base, so it needs the traps in
[qt-build-traps](../qt-build-traps/SKILL.md): `QObject::connect`, no `Q_OBJECT`, signals in a non-template class.

## What the fixtures cover

Lists in full (the contract run, ranges, edits, thread assertion, nothrow move) and the five row indexes against a
plain vector. A keyed model (map, hash, set, multi) over the indexes has no fixture here; the reflect-moc
repository has one for each container. Evidence: [evidence](references/evidence.md).
