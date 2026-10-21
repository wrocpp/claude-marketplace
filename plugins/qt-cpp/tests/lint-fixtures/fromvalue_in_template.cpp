#include <QObject>

template <class Key>
class Announcer : public QObject {
 public:
  void announce(const Key& key) {
    emit added(QVariant::fromValue(key));  // FINDING fromvalue-in-template-emit
  }
  void announceLater(Key* key) { Q_EMIT added(QVariant::fromValue(key)); }  // FINDING fromvalue-in-template-emit
 signals:
  void added(const QVariant&);
};

template <class T>
void free_function(QObject* o, T* p) {
  emit o->destroyed(QVariant::fromValue(p));  // FINDING fromvalue-in-template-emit
}
