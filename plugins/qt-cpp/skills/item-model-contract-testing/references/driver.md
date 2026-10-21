# The driver, `include/qt_cpp/model_contract.hpp`

```cpp
#include <qt_cpp/model_contract.hpp>

const auto report = qt_cpp::contract::run_random<MySource>(
    {.seed = 7, .steps = 4000, .with_proxy = true, .with_tester = true},
    [](MySource* source) { return std::make_unique<MyModel>(source); });
CHECK(report.clean());                       // report.violations and report.mismatches say what went wrong
```

`MySource` is default-constructible and offers `qsizetype size() const` and `bool insert(int row, int value)`,
`remove(int row)`, `replace(int row, int value)`, `move(int from, int to)`, `clear()`. Each returns false and
changes nothing for an invalid request; `move` leaves the entry at row `to`. The model shows `value` as
`Qt::DisplayRole`. Wrap your container in a small adapter with those six calls; do not change the container.

| option | default | meaning |
|---|---|---|
| `seed`, `steps` | 1, 1000 | the run is reproducible from the seed |
| `with_mirror` | true | off: only checks on the model's own data run (the control that shows what the mirror adds) |
| `stop_at_first_violation` | false | stop where the fault first shows; use it for every control run |
| `with_proxy` | false | a `QSortFilterProxyModel` sorted by display value, with a second mirror |
| `with_tester` | false | `QAbstractItemModelTester`, Fatal: leave it off for a wrong adapter |
| `stable_key_role` | none | a role the model promises is a stable key; none means `Qt::UserRole` must be empty |

## What each check catches

| mistake | reported by |
|---|---|
| `beginInsertRows` without `endInsertRows` | mirror: "a change was announced and never confirmed" |
| removal announced for the wrong row | mirror: a row shows another entry's value |
| value changed, no `dataChanged` | mirror only; every check on the model's own data passes |
| row used as a key | `Qt::UserRole` not empty, or the mirror when `stable_key_role` is set |
| selection or persistent index drifts | selection and persistent-index checks |
| a proxy that is out of step | the proxy mirror and the proxy's expected order |

Extend, do not fork: a keyed container (map, hash, set) needs a reference that finds an entry by key instead of by
row; keep the mirror, the tester, the selection and the proxy as they are.
