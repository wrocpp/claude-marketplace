// Adapters with one deliberate mistake each, the kind that produces ghost rows when the wiring between a source and a
// view is written by hand. They exist so that the contract run is shown to fail on a wrong model, and not only to pass
// on a right one.
#pragma once

#include "observable_list.hpp"

#include <QtCore/QAbstractListModel>

namespace qt_cpp_test {

enum class Flaw {
  none,
  forgot_end_insert,  // beginInsertRows with no endInsertRows
  wrong_row_remove,   // the removal is announced for the next row
  silent_replace,     // a value changes and no dataChanged follows
  row_as_key,         // data() answers the key role with the row
};

inline const char* name_of(Flaw flaw) {
  switch (flaw) {
    case Flaw::none: return "none";
    case Flaw::forgot_end_insert: return "forgot_end_insert";
    case Flaw::wrong_row_remove: return "wrong_row_remove";
    case Flaw::silent_replace: return "silent_replace";
    case Flaw::row_as_key: return "row_as_key";
  }
  return "?";
}

class FlawedListModel : public QAbstractListModel {
 public:
  using Source = ObservableList<int>;
  static constexpr int KeyRole = Qt::UserRole;

  FlawedListModel(Source* source, Flaw flaw) : m_source(source), m_flaw(flaw) {
    connect(source, &Source::aboutToInsert, this, [this](int first, int last) { beginInsertRows(QModelIndex(), first, last); });
    connect(source, &Source::inserted, this, [this](int, int) {
      if (m_flaw == Flaw::forgot_end_insert) return;
      endInsertRows();
    });
    connect(source, &Source::aboutToRemove, this, [this](int first, int last) {
      const int count = static_cast<int>(m_source->size());
      const bool wrong = m_flaw == Flaw::wrong_row_remove && last + 1 < count;
      beginRemoveRows(QModelIndex(), wrong ? first + 1 : first, wrong ? last + 1 : last);
    });
    connect(source, &Source::removed, this, [this](int, int) { endRemoveRows(); });
    connect(source, &Source::changed, this, [this](int row) {
      if (m_flaw != Flaw::silent_replace) emit dataChanged(index(row), index(row));
    });
    connect(source, &Source::aboutToMove, this, [this](int from, int to) {
      beginMoveRows(QModelIndex(), from, from, QModelIndex(), to > from ? to + 1 : to);
    });
    connect(source, &Source::moved, this, [this](int, int) { endMoveRows(); });
    connect(source, &Source::aboutToClear, this, [this] { beginResetModel(); });
    connect(source, &Source::cleared, this, [this] { endResetModel(); });
  }

  int rowCount(const QModelIndex& parent = QModelIndex()) const override { return parent.isValid() ? 0 : static_cast<int>(m_source->size()); }

  QVariant data(const QModelIndex& index, int role = Qt::DisplayRole) const override {
    if (!index.isValid() || index.row() >= rowCount()) return {};
    if (role == Qt::DisplayRole) return m_source->at(index.row());
    // qt-model-ok: the flaw this class exists to show; the row shifts under every insert, with no signal
    if (role == KeyRole && m_flaw == Flaw::row_as_key) return index.row();
    return {};
  }

 private:
  Source* m_source;
  Flaw m_flaw;
};

}  // namespace qt_cpp_test
