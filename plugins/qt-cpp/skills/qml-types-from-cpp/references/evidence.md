# Evidence: qml-types-from-cpp

`tests/cpp/qml_types.cpp`, GCC 16.2.0, Debug build, headless (QtQml, no window), Linux aarch64.

| step | Qt 6.8.2 | Qt 6.10.3 |
|---|---|---|
| `qmlRegisterType<Dial>`, `Dial { value: 3; onValueChanged: function(value) {...} }`, then `bump()` from QML: handler heard 9 | pass | pass |
| the handler had not run for the value set at creation (`heard` still -1) | pass | pass |
| `setContextProperty("dial", &dial)` and `property int shown: dial.value` followed a later change | pass | pass |
| `setContextProperty("items", &model)` and an `Instantiator` whose `count` went 0, 3, 2 across three inserts and one remove | pass | pass |

Not covered here: a class template specialization registered with `qmlRegisterType`. The reflect-moc repository runs it
(`capability_class_template_qml`); this plugin has no fixture for it.
