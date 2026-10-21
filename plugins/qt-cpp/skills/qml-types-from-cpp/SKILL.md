---
name: qml-types-from-cpp
description: Use when exposing a C++ class, an object or an item model to QML - registering a type with qmlRegisterType or QML_ELEMENT, handling a C++ signal in QML with its argument names, binding a property that has a NOTIFY signal, setting a context property, or feeding a model to an Instantiator. Thin on purpose - only what a headless fixture here ran. Trigger phrases - "qmlRegisterType", "QML_ELEMENT", "onSomethingChanged: function", "signal handler argument", "setContextProperty", "context property model", "Q_PROPERTY NOTIFY binding", "Instantiator model", "register a C++ type in QML".
---

# QML types from C++

Everything here is run by `${CLAUDE_PLUGIN_ROOT}/tests/cpp/qml_types.cpp`: QtQml only, no window, a
`QCoreApplication`. Evidence in [evidence](references/evidence.md).

1. **Register a type** with `qmlRegisterType<T>("module.name", major, minor, "Name")` (the call `QML_ELEMENT`
   generates), then `import module.name` in the QML. QML creates the element and sets its properties from the
   `Q_PROPERTY` write function.
2. **Handle a signal by name, with its arguments named.** For `void valueChanged(int value)` write
   `onValueChanged: function(value) { ... }`. The argument arrives as its own type, not as a `QVariant`.
3. **A property that is set where the element is created does not run the handler**: the handler is connected after
   the initial values are applied (`value: 3` leaves `heard` untouched in the fixture). A later change does.
4. **An object as a context property** (`engine.rootContext()->setContextProperty("dial", &dial)`) works with a
   binding (`property int shown: dial.value`) when the property has a `NOTIFY` signal: the binding follows it.
5. **A model as a context property** is followed by an `Instantiator { model: items; delegate: ... }`; its `count`
   tracks inserts and removes. A model whose begin/end calls are wrong breaks this too, so contract-test it first
   ([item-model-contract-testing](../item-model-contract-testing/SKILL.md)).
6. **A class template specialization** registered with `qmlRegisterType` needs a normalized class name, or Qt aborts
   when it registers the pointer type ([qt-build-traps](../qt-build-traps/SKILL.md)). With reflect-moc this was run
   by the reflect-moc repository itself (`capability_class_template_qml`), not by a fixture here.

Not covered: QML_ELEMENT through `qt_add_qml_module`, Qt Quick items and views, `QQmlEngine` ownership rules,
`Q_INVOKABLE` argument conversion beyond `void()`.
