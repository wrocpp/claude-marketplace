// A C++ type in QML, headless (QtQml only, no window): QML creates a registered type, sets its property, handles its
// signal by name with the argument as its own type, an object is a context property with a binding, and a list model
// is a context property that a QML Instantiator follows. qmlRegisterType is the call QML_ELEMENT generates.
#include "check.hpp"
#include "list_model.hpp"

#include <QtCore/QCoreApplication>
#include <QtCore/QVariant>
#include <QtQml/QQmlComponent>
#include <QtQml/QQmlContext>
#include <QtQml/QQmlEngine>

#include <cstdio>
#include <memory>

namespace {
constexpr int kMajor = 1;
constexpr int kMinor = 0;
constexpr int kInitial = 3;
constexpr int kBumped = 9;
constexpr int kRows = 3;

class Dial : public QObject {
  Q_OBJECT
  Q_PROPERTY(int value READ value WRITE setValue NOTIFY valueChanged)

 public:
  int value() const { return m_value; }
  Q_INVOKABLE void bump() { setValue(kBumped); }
  void setValue(int value) {
    if (value == m_value) return;
    m_value = value;
    emit valueChanged(value);
  }

 signals:
  void valueChanged(int value);

 private:
  int m_value = 0;
};

std::unique_ptr<QObject> create(QQmlEngine& engine, const char* source) {
  QQmlComponent component(&engine);
  component.setData(source, QUrl{});
  std::unique_ptr<QObject> root{component.create()};
  if (!root) std::fprintf(stderr, "QML errors: %s\n", component.errorString().toUtf8().constData());
  return root;
}

void registered_type_and_handler() {
  CHECK(qmlRegisterType<Dial>("qtcpp.test", kMajor, kMinor, "Dial") >= 0);
  QQmlEngine engine;
  const auto root = create(engine, R"(
    import QtQml
    import qtcpp.test
    QtObject {
      id: root
      property int heard: -1
      property var dial: Dial {
        value: 3
        onValueChanged: function(value) { root.heard = value }
      }
      function bump() { dial.bump() }
    }
  )");
  CHECK(root);
  if (!root) return;
  auto* dial = qobject_cast<Dial*>(root->property("dial").value<QObject*>());
  CHECK(dial != nullptr);
  if (!dial) return;
  CHECK(dial->value() == kInitial);
  CHECK(root->property("heard").toInt() == -1);  // set while the element is created: no handler ran yet
  CHECK(QMetaObject::invokeMethod(root.get(), "bump"));
  CHECK(dial->value() == kBumped);
  CHECK(root->property("heard").toInt() == kBumped);
}

void object_as_context_property() {
  Dial dial;
  QQmlEngine engine;
  engine.rootContext()->setContextProperty("dial", &dial);
  const auto root = create(engine, R"(
    import QtQml
    QtObject { property int shown: dial.value }
  )");
  CHECK(root);
  if (!root) return;
  CHECK(root->property("shown").toInt() == 0);
  dial.setValue(kBumped);
  CHECK(root->property("shown").toInt() == kBumped);  // the binding followed the NOTIFY signal
}

void model_as_context_property() {
  qt_cpp_test::ObservableList<int> list;
  qt_cpp_test::IntListModel model(&list);
  QQmlEngine engine;
  engine.rootContext()->setContextProperty("items", &model);
  const auto root = create(engine, R"(
    import QtQml
    QtObject {
      property var follower: Instantiator { model: items; delegate: QtObject { property int number: model.display } }
      property int count: follower.count
    }
  )");
  CHECK(root);
  if (!root) return;
  CHECK(root->property("count").toInt() == 0);
  for (int row = 0; row < kRows; ++row) list.insert(row, row + 1);
  CHECK(root->property("count").toInt() == kRows);
  list.remove(0);
  CHECK(root->property("count").toInt() == kRows - 1);
}
}  // namespace

int main(int argc, char** argv) {
  QCoreApplication app(argc, argv);
  registered_type_and_handler();
  object_as_context_property();
  model_as_context_property();
  return qt_cpp_test::finish("qml_types");
}

#include "qml_types.moc"
