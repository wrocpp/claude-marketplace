// Needs reflect-moc, GCC 16.2 and Qt 6.10 (see run.sh); prints SKIP otherwise.
// A pointer to a class template specialization goes into a QVariant: Qt registers it under className() + "*" and,
// in a debug build, aborts on a name it would normalize differently. The class name reflect-moc reports is already in
// Qt's form for every spelling a compiler gives a specialization, so the round trip works.
#include "../cpp/check.hpp"
#include "reflect_moc_class_template.hpp"

#include <QtCore/QCoreApplication>
#include <QtCore/QVariant>

int main(int argc, char** argv) {
  QCoreApplication app(argc, argv);
  using namespace optional_fixture;

  Keyed<unsigned> hashed;
  Keyed<QList<unsigned char>> nested;
  Pair<QHash<unsigned, int>, QList<QList<int>>> pair;

  for (const QObject* object : {static_cast<const QObject*>(&hashed), static_cast<const QObject*>(&nested), static_cast<const QObject*>(&pair)}) {
    const QByteArray name = object->metaObject()->className();
    CHECK(name == QMetaObject::normalizedType(name.constData()));
  }
  CHECK(QByteArray{hashed.metaObject()->className()} == "optional_fixture::Keyed<uint>");
  CHECK(QByteArray{nested.metaObject()->className()} == "optional_fixture::Keyed<QList<uchar>>");

  CHECK(QVariant::fromValue(&hashed).value<Keyed<unsigned>*>() == &hashed);
  CHECK(QVariant::fromValue(&nested).value<Keyed<QList<unsigned char>>*>() == &nested);
  CHECK(QVariant::fromValue(&pair).isValid());

  int heard = 0;
  QObject::connect(&hashed, &Keyed<unsigned>::added, &hashed, [&heard](const unsigned&) { ++heard; });
  hashed.add(1u);
  CHECK(heard == 1);
  return qt_cpp_test::finish("reflect_moc_class_template_normalized");
}
