#include <QAbstractListModel>

template <class Model>
class Wired : public Model {
 public:
  Wired(QObject* source) {
    connect(source, SIGNAL(changed()), this, SLOT(refresh()));  // FINDING dependent-base-connect
  }
  void again(QObject* source) {
    if (source) connect(source, SIGNAL(changed()), this, SLOT(refresh()));  // FINDING dependent-base-connect
    const auto link = connect(source, SIGNAL(changed()), this, SLOT(refresh()));  // FINDING dependent-base-connect
    (void)link;
  }
};

template <class Source, class Model>
class Typed : public Wrapper<Model> {
 public:
  Typed(Source* source) {
    connect(source, &Source::changed, this, [] {});  // FINDING dependent-base-connect
  }
};

template <class T>
struct Outer : T {
  struct Inner {
    void go(QObject* a) { connect(a, SIGNAL(x()), a, SLOT(y())); }  // FINDING dependent-base-connect
  };
};
