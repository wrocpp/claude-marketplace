// The end lives in the paired slot, and the marker says where.
#include <QAbstractListModel>

class Split : public QAbstractListModel {
 public:
  void onAboutToInsert(int row) {
    // qt-model-ok: ended in onInserted
    beginInsertRows(QModelIndex(), row, row);
  }
  void onInserted() { endInsertRows(); }
  void onAboutToRemove(int row) {
    beginRemoveRows(QModelIndex(), row, row);  // qt-model-ok: ended in onRemoved
  }
  void onRemoved() { endRemoveRows(); }
};
