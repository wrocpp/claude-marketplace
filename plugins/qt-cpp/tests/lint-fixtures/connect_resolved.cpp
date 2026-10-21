// None of these is the trap: a qualified call, this->, a base that does not depend on a parameter, a class that
// is not a template, a member named connect, a declaration, and connect used as a word.
#include <QAbstractListModel>

template <class Model>
class Qualified : public Model {
 public:
  Qualified(QObject* source) {
    QObject::connect(source, SIGNAL(changed()), this, SLOT(refresh()));
    this->connect(source, SIGNAL(changed()), this, SLOT(refresh()));
    Model::connect(source, SIGNAL(changed()), this, SLOT(refresh()));
    // connect(source, ...) in a comment
    const char* word = "connect(a, b)";
    (void)word;
  }
};

template <class T>
class FixedBase : public QAbstractListModel {
 public:
  FixedBase(QObject* source) { connect(source, SIGNAL(changed()), this, SLOT(refresh())); }
  T value;
};

class NotATemplate : public QAbstractListModel {
 public:
  NotATemplate(QObject* source) { connect(source, SIGNAL(changed()), this, SLOT(refresh())); }
};

template <class Model>
class OwnConnect : public Model {
 public:
  bool connect(int port);
  void use() { connect(1); }
};
