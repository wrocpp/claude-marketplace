// expect-error: Template classes not supported by Q_OBJECT
// moc rejects Q_OBJECT in a class template. Put the signals in a class that is not a template and derive the template
// from it (list_signals.hpp and observable_list.hpp), or give the template no signals. A model that is not Q_OBJECT
// still works as a QAbstractListModel subclass (list_model.hpp).
#include <QtCore/QObject>

template <class T>
class Counter : public QObject {
  Q_OBJECT

 public:
  void bump(const T& value) { emit changed(value); }

 signals:
  void changed(const T& value);
};

#include "q_object_in_template_by_moc.moc"
