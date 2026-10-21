// A class template with typed signals, built on reflect-moc (a Qt 6.10 + GCC 16.2 reflection layer that replaces moc).
// moc rejects Q_OBJECT in a class template; reflect-moc does not, because the meta-object is made from the class by
// reflection. The class name Qt sees is the compiler's spelling of the specialization in Qt's normalized form.
#pragma once

#include <reflect_moc/qt/qt.hpp>

#include <QtCore/QHash>
#include <QtCore/QList>
#include <QtCore/QMetaObject>
#include <QtCore/QObject>

#include <typeinfo>

namespace optional_fixture {

template <class K>
class Keyed : public QObject {
  RQT_OBJECT

 public:
  void add(const K& key) {
    emit added(key);
    ++count;
  }
  int count = 0;

 signals:
  rqt::signal<void(const K&)> added;
};

template <class A, class B>
class Pair : public QObject {
  RQT_OBJECT

 signals:
  rqt::signal<void()> done;
};

using Container = Keyed<QHash<unsigned, int>>;

// defined in the second translation unit
void add_from_second_unit(Container* container, const QHash<unsigned, int>& key);
const QMetaObject* meta_in_second_unit();
int added_index_in_second_unit();
char const* signal_type_name_in_second_unit();

}  // namespace optional_fixture
