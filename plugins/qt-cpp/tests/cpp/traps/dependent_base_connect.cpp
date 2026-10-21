// In a class template whose base is a template parameter, an unqualified connect(...) is not looked up in the
// base: ordinary lookup does not enter a dependent base, so only argument-dependent lookup is left. Whatever
// function called connect that lives in a namespace of an argument is found instead, and nothing is connected, with
// no diagnostic. QObject::connect and this->connect reach the right one.
#include "../check.hpp"

#include <QtCore/QCoreApplication>
#include <QtCore/QObject>

namespace decoy {
inline int calls = 0;
// A function of this name in the namespace of the sender's type, as a library of signals and slots would have.
template <class... Args>
void connect(Args&&...) {
  ++calls;
}

class Emitter : public QObject {
  Q_OBJECT
 public:
  void fire() { emit fired(); }
 signals:
  void fired();
};
}  // namespace decoy

template <class Base>
struct Unqualified : Base {
  // qt-model-ok: the trap this fixture shows
  explicit Unqualified(decoy::Emitter* sender, int* hits) { connect(sender, &decoy::Emitter::fired, this, [hits] { ++*hits; }); }
};
template <class Base>
struct Qualified : Base {
  explicit Qualified(decoy::Emitter* sender, int* hits) { QObject::connect(sender, &decoy::Emitter::fired, this, [hits] { ++*hits; }); }
};
template <class Base>
struct ThroughThis : Base {
  explicit ThroughThis(decoy::Emitter* sender, int* hits) { this->connect(sender, &decoy::Emitter::fired, this, [hits] { ++*hits; }); }
};

template <template <class> class Wired>
int hits_after_one_signal() {
  decoy::Emitter sender;
  int hits = 0;
  Wired<QObject> receiver(&sender, &hits);
  sender.fire();
  return hits;
}

int main(int argc, char** argv) {
  QCoreApplication app(argc, argv);
  using namespace qt_cpp_test;
  CHECK(hits_after_one_signal<Unqualified>() == 0);  // the decoy was called, the signal was never connected
  CHECK(decoy::calls == 1);
  CHECK(hits_after_one_signal<Qualified>() == 1);
  CHECK(hits_after_one_signal<ThroughThis>() == 1);
  CHECK(decoy::calls == 1);  // the two right forms did not touch it
  return finish("dependent_base_connect");
}

#include "dependent_base_connect.moc"
