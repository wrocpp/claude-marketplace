// QVariant::fromValue outside an emit, and an emit outside a template, are not the rule.
#include <QObject>

template <class Key>
class Typed : public QObject {
 public:
  void announce(const Key& key) { emit added(key); }
  QVariant boxed(const Key& key) const { return QVariant::fromValue(key); }
 signals:
  void added(const Key&);
};

class Plain : public QObject {
 public:
  void announce(int key) { emit added(QVariant::fromValue(key)); }
 signals:
  void added(const QVariant&);
};
