#include <QAbstractListModel>

class ByIf : public QAbstractListModel {
 public:
  enum Roles { KeyRole = Qt::UserRole, LabelRole };
  QVariant data(const QModelIndex& index, int role) const override {
    if (role == Qt::DisplayRole) return m_labels.at(index.row());
    if (role == KeyRole) return index.row();  // FINDING row-as-key
    return {};
  }
  QStringList m_labels;
};

class BySwitch : public QAbstractListModel {
 public:
  enum Roles { IdRole = Qt::UserRole + 1 };
  QVariant data(const QModelIndex& idx, int r) const override {
    switch (r) {
      case Qt::DisplayRole:
        return idx.row();
      case IdRole:
        return QVariant::fromValue(idx.row());  // FINDING row-as-key
    }
    return {};
  }
};

class ViaLocal : public QAbstractListModel {
 public:
  static constexpr int kEntryKeyRole = Qt::UserRole;
  QVariant data(const QModelIndex& index, int role = Qt::DisplayRole) const override {
    const int row = index.row();
    if (kEntryKeyRole == role) {
      return row;  // FINDING row-as-key
    }
    return {};
  }
};

QVariant Outside::data(const QModelIndex& index, int role) const {
  if (role == Roles::ItemKeyRole) return static_cast<int>(index.row()) + 0;  // FINDING row-as-key
  return {};
}
