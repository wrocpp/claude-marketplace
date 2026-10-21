---
name: item-model-contract-testing
description: Use when writing, changing or reviewing a Qt item model (a QAbstractListModel, QAbstractTableModel or QAbstractItemModel subclass, or a QSortFilterProxyModel on top of one) or a test for it. Tests a model against a view mirror built from its signals only, a seeded random driver, QAbstractItemModelTester in Fatal mode, selection and persistent-index survival and a sorting proxy, and proves the test by running deliberately wrong adapters that it must reject. Trigger phrases - "test my model", "QAbstractItemModelTester", "ghost rows", "beginInsertRows", "endInsertRows", "missing dataChanged", "view out of sync with the model", "ListView shows stale rows", "sort filter proxy wrong order", "random test for a model", "fuzz a model", "persistent index", "model contract".
---

# Item model contract testing

A model reads its container live, so a check on the model's own data is always right about itself. A view is not: it
knows only what the signals told it. Test the model through the view's eyes.

## The test

1. **Mirror from signals only.** Keep a row cache updated by `rowsInserted`, `rowsRemoved`, `rowsMoved`,
   `modelReset`, `dataChanged` and `layoutChanged`, and nothing else. After every change compare it with the live
   model. It catches a wrong row in `beginRemoveRows`, a missing `dataChanged`, an end call that never comes, an
   announcement made after the change, and a value that shifts with no signal.
2. **Seeded random changes against a plain reference** (insert, remove, replace, move, clear, select), with invalid
   rows mixed in so refusals are tested too. Print the seed.
3. **`QAbstractItemModelTester` in Fatal mode** on the right model only: on a wrong model it aborts before your
   report is printed.
4. **Selection and a `QPersistentModelIndex`** that must follow their entries (track them by an id the reference
   keeps), and be invalid once the entry is gone.
5. **A sorting proxy** (`QSortFilterProxyModel`) on top, with its own mirror: it re-reads the model from the same
   signals, so a wrong announcement leaves its rows out of order.
6. **Controls.** For every rule the test claims to enforce, a deliberately wrong adapter the same driver must
   report. A test that only passes on the right model proves nothing. Control runs stop at the first violation
   (`stop_at_first_violation`): after a wrong adapter Qt's own bookkeeping is unbalanced and a longer run can crash.

`${CLAUDE_PLUGIN_ROOT}/include/qt_cpp/model_contract.hpp` is all of this for a list model: copy it into the project
(it has no dependency but Qt Core and Qt Test). Its source contract and options are in
[the driver reference](references/driver.md). The right model and four wrong adapters it is proved against are in
`${CLAUDE_PLUGIN_ROOT}/tests/cpp/list_model.hpp` and `${CLAUDE_PLUGIN_ROOT}/tests/cpp/flawed_models.hpp`.

## Rules the driver encodes

- A role is a **stable key** only if its value follows its entry. A list offers none: the row shifts under every
  insert and remove with no signal, and a sorting proxy that caches it goes stale. The mirror takes
  `stable_key_role` to test a role that claims to be stable; without it the driver asserts `Qt::UserRole` is empty.
- A **mirror must re-read after `layoutChanged`**: a proxy re-sorts after a value change and says so only that way.
- A refused request (row out of range, `from == to`) changes nothing and announces nothing; the driver checks the
  source and the reference agree on every refusal.
- Run the contract once per model type, not once per container: a generic base that pairs every begin with its end
  once ([container-to-model-patterns](../container-to-model-patterns/SKILL.md)) needs one run per base.

## What it does not cover

Table and tree models (the driver is list-shaped: one column, no children), editing through delegates, threads,
and a model with no source object to drive. The evidence table, with the Qt versions each fixture was run on, is in
[evidence](references/evidence.md).
