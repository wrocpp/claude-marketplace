#include <QAbstractListModel>

class Names : public QAbstractListModel {
 public:
  void append(const QString& name) {
    beginInsertRows(QModelIndex(), m_names.size(), m_names.size());  // FINDING begin-end-pairing
    m_names.append(name);
  }
  void removeAt(int row) {
    beginRemoveRows(QModelIndex(), row, row);
    m_names.removeAt(row);
    endRemoveRows();
  }
  void reset() {
    this->beginResetModel();  // FINDING begin-end-pairing
    m_names.clear();
  }
  void moveFirstToEnd() {
    beginMoveRows(QModelIndex(), 0, 0, QModelIndex(), m_names.size());  // FINDING begin-end-pairing
    m_names.move(0, m_names.size() - 1);
    endInsertRows();  // the wrong end: it does not close a move
  }

 private:
  QStringList m_names;
};
