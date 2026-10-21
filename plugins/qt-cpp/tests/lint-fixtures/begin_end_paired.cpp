// Every begin has its end in the same function: in one body, in two lambdas of one wiring function, in a template.
#include <QAbstractListModel>

class Paired : public QAbstractListModel {
 public:
  void append(const QString& name) {
    beginInsertRows(QModelIndex(), m_names.size(), m_names.size());
    m_names.append(name);
    endInsertRows();
  }
  void reset(const QStringList& names) {
    if (names == m_names) return;
    beginResetModel();
    m_names = names;
    endResetModel();
  }
  void wire(QObject* source) {
    connect(source, SIGNAL(aboutToInsert(int)), this, [this](int row) { beginInsertRows(QModelIndex(), row, row); });
    connect(source, SIGNAL(inserted(int)), this, [this](int) { endInsertRows(); });
  }
  // A begin named in a comment or a string is not a call: beginInsertRows( without an end
  const char* text() const { return "beginRemoveRows( is only text here"; }

 private:
  QStringList m_names;
};

template <class Source, class Model = QAbstractListModel>
class Base : public Model {
 public:
  explicit Base(Source* source) {
    QObject::connect(source, &Source::aboutToClear, this, [this] { this->beginResetModel(); });
    QObject::connect(source, &Source::cleared, this, [this] { this->endResetModel(); });
  }
};
