// expect-error: .signals. does not name a type
// With QT_NO_KEYWORDS defined `signals:` and `emit` stop existing, so a header that copies the define from another
// file and still uses them no longer compiles. Spell them Q_SIGNALS and Q_EMIT in such a header.
#define QT_NO_KEYWORDS
#include <QtCore/QObject>

class Counter : public QObject {
 public:
  void bump() { emit changed(1); }
 signals:
  void changed(int value);
};
