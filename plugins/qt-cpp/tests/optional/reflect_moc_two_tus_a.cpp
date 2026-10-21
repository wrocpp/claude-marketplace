// Needs reflect-moc, GCC 16.2 and Qt 6.10 (see run.sh); prints SKIP otherwise.
// One specialization of a class template with typed signals, instantiated in two translation units and linked with
// -flto -Wodr -Wlto-type-mismatch -Werror. The meta-object is one object, the signal index is the same in both, and
// a signal member has one type in both: a second definition of anything would be reported at link time.
#include "../cpp/check.hpp"
#include "reflect_moc_class_template.hpp"

#include <QtCore/QCoreApplication>
#include <QtCore/QMetaMethod>

#include <cstring>

int main(int argc, char** argv) {
  QCoreApplication app(argc, argv);
  using namespace optional_fixture;

  Container container;
  CHECK(&Container::staticMetaObject == meta_in_second_unit());
  CHECK(QMetaMethod::fromSignal(&Container::added).methodIndex() == added_index_in_second_unit());
  char const* const mine = typeid(container.added).name();
  CHECK(std::strcmp(mine, signal_type_name_in_second_unit()) == 0);
  CHECK(mine[0] != '*');  // GCC marks a type with internal linkage with a leading '*'

  int heard = 0;
  QObject::connect(&container, &Container::added, &container, [&heard](const QHash<unsigned, int>&) { ++heard; });
  add_from_second_unit(&container, {});  // announced from the other unit
  container.add({});                     // and from this one
  CHECK(heard == 2);
  return qt_cpp_test::finish("reflect_moc_two_tus");
}
