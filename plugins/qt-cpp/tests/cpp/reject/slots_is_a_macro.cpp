// expect-error: expected unqualified-id
// `slots` and `signals` are macros (for keywords) once a Qt header is included, so they cannot be a method or a
// variable name. Define QT_NO_KEYWORDS and write Q_SLOTS and Q_SIGNALS, or pick another name.
#include <QtCore/QObject>

struct Layout {
  int slots() const { return count; }
  int count = 0;
};
