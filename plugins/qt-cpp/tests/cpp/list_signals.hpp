// The signals of an observable list, in a class that is not a template: moc rejects Q_OBJECT in a class template,
// so the signals live here and the template (observable_list.hpp) derives from it. Rows are ints, so nothing needs
// boxing in a QVariant.
#pragma once

#include <QtCore/QObject>

namespace qt_cpp_test {

class ListSignals : public QObject {
  Q_OBJECT

 public:
  using QObject::QObject;

 signals:
  void aboutToInsert(int first, int last);
  void inserted(int first, int last);
  void aboutToRemove(int first, int last);
  void removed(int first, int last);
  void changed(int row);
  void aboutToMove(int from, int to);
  void moved(int from, int to);
  void aboutToClear();
  void cleared();
};

}  // namespace qt_cpp_test
