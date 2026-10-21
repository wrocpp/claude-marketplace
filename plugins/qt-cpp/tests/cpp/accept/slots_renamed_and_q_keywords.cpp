// What slots_is_a_macro.cpp and qt_no_keywords_removes_signals.cpp ask for: another name, and the Q_ spellings under
// QT_NO_KEYWORDS.
#define QT_NO_KEYWORDS
#include <QtCore/QObject>

struct Layout {
  int slotCount() const { return count; }
  int count = 0;
};

class Counter : public QObject {
 public:
  void bump() { Q_EMIT changed(1); }
 Q_SIGNALS:
  void changed(int value);
};
