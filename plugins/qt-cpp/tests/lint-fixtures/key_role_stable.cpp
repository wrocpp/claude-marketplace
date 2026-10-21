// A key role that answers with something that belongs to the entry; the row is fine for other roles.
#include <QAbstractListModel>

class Stable : public QAbstractListModel {
 public:
  enum Roles { KeyRole = Qt::UserRole, PositionRole };
  QVariant data(const QModelIndex& index, int role) const override {
    if (role == KeyRole) return m_entries.at(index.row()).id;
    if (role == PositionRole) return index.row();  // a position, not a key, and not a stable one by name
    if (role == Qt::DisplayRole) return index.row();
    return {};
  }
  struct Entry { int id; };
  QList<Entry> m_entries;
};

class NoKeyRole : public QAbstractListModel {
 public:
  QVariant data(const QModelIndex& index, int role) const override {
    return role == Qt::DisplayRole ? QVariant(m_labels.at(index.row())) : QVariant();
  }
  QStringList m_labels;
};
