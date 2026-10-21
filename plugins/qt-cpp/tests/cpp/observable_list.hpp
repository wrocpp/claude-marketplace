// A QList that announces every change before and after it is made, the source of the list models in these tests.
// Every mutation is announced once; a request that cannot be honoured returns false and announces nothing.
#pragma once

#include "list_signals.hpp"

#include <QtCore/QList>

#include <type_traits>
#include <utility>

namespace qt_cpp_test {

template <class T>
class ObservableList : public ListSignals {
 public:
  // A Qt container allocates inside the insert, so nothing can be prepared before the "about" signal and a throw
  // cannot be undone: a throw between the two signals leaves every model mid-change. Refuse at compile time what
  // can be refused.
  static_assert(std::is_nothrow_move_constructible_v<T> && std::is_nothrow_move_assignable_v<T>,
                "ObservableList: the value type must be nothrow move constructible and assignable, because a throw "
                "between the 'about' and the 'done' signal leaves every model mid-change");

  using ListSignals::ListSignals;

  qsizetype size() const { return m_items.size(); }
  const T& at(int row) const { return m_items.at(row); }

  bool insert(int row, T value) {
    if (row < 0 || row > size()) return false;
    emit aboutToInsert(row, row);
    m_items.insert(row, std::move(value));
    emit inserted(row, row);
    return true;
  }

  // A run is one change: one begin and one end for a model, however long it is.
  bool insertRange(int row, QList<T> values) {
    if (row < 0 || row > size() || values.isEmpty()) return false;
    const int last = row + static_cast<int>(values.size()) - 1;
    emit aboutToInsert(row, last);
    for (qsizetype i = 0; i < values.size(); ++i) m_items.insert(row + i, std::move(values[i]));
    emit inserted(row, last);
    return true;
  }

  bool remove(int row) { return removeRange(row, row); }

  bool removeRange(int first, int last) {
    if (first < 0 || last < first || last >= size()) return false;
    emit aboutToRemove(first, last);
    m_items.remove(first, last - first + 1);
    emit removed(first, last);
    return true;
  }

  bool replace(int row, T value) {
    if (row < 0 || row >= size()) return false;
    m_items[row] = std::move(value);
    emit changed(row);
    return true;
  }

  // The entry at `from` ends at row `to`.
  bool move(int from, int to) {
    if (from < 0 || to < 0 || from >= size() || to >= size() || from == to) return false;
    emit aboutToMove(from, to);
    m_items.move(from, to);
    emit moved(from, to);
    return true;
  }

  bool clear() {
    if (m_items.isEmpty()) return false;
    emit aboutToClear();
    m_items.clear();
    emit cleared();
    return true;
  }

 private:
  QList<T> m_items;
};

}  // namespace qt_cpp_test
