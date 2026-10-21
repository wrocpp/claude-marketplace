// The right list model: every begin and its end are paired once, in the one base, driven by the source's
// about/done signals. A concrete model adds data() and nothing else, so a new data type cannot get the
// bookkeeping wrong. No key role is offered: the only identity of a list entry is its row, which shifts under every
// insert and remove with no signal.
//
// The base is a class template with a dependent base (Model), so connect is written QObject::connect and every
// inherited member is reached through this->. It has no Q_OBJECT: a model with no signals or slots of its own does
// not need one, and moc would reject a class template.
#pragma once

#include "observable_list.hpp"

#include <QtCore/QAbstractListModel>
#include <QtCore/QThread>

namespace qt_cpp_test {

template <class Source, class Model = QAbstractListModel>
class ListModelBase : public Model {
 public:
  int rowCount(const QModelIndex& parent = QModelIndex()) const override {
    return parent.isValid() ? 0 : static_cast<int>(m_source->size());
  }

 protected:
  explicit ListModelBase(Source* source, QObject* parent = nullptr) : Model(parent), m_source(source) {
    // A source and its models live in one thread, so the connections are direct; assert it in a debug build.
    Q_ASSERT_X(source->thread() == this->thread(), "ListModelBase", "a model must live in the thread of its source");
    connectSource();
  }

  Source* source() const { return m_source; }

 private:
  void connectSource() {
    QObject::connect(m_source, &Source::aboutToInsert, this, [this](int first, int last) { this->beginInsertRows(QModelIndex(), first, last); });
    QObject::connect(m_source, &Source::inserted, this, [this](int, int) { this->endInsertRows(); });
    QObject::connect(m_source, &Source::aboutToRemove, this, [this](int first, int last) { this->beginRemoveRows(QModelIndex(), first, last); });
    QObject::connect(m_source, &Source::removed, this, [this](int, int) { this->endRemoveRows(); });
    QObject::connect(m_source, &Source::changed, this, [this](int row) {
      const QModelIndex changed = this->index(row, 0);
      emit this->dataChanged(changed, changed);
    });
    QObject::connect(m_source, &Source::aboutToMove, this, [this](int from, int to) {
      // beginMoveRows takes the row the block is put before, so a move down counts one further.
      this->beginMoveRows(QModelIndex(), from, from, QModelIndex(), to > from ? to + 1 : to);
    });
    QObject::connect(m_source, &Source::moved, this, [this](int, int) { this->endMoveRows(); });
    QObject::connect(m_source, &Source::aboutToClear, this, [this] { this->beginResetModel(); });
    QObject::connect(m_source, &Source::cleared, this, [this] { this->endResetModel(); });
  }

  Source* m_source;
};

class IntListModel : public ListModelBase<ObservableList<int>> {
 public:
  using Source = ObservableList<int>;

  explicit IntListModel(Source* source, QObject* parent = nullptr) : ListModelBase(source, parent) {}

  QVariant data(const QModelIndex& index, int role = Qt::DisplayRole) const override {
    if (!index.isValid() || index.row() >= rowCount() || role != Qt::DisplayRole) return {};
    return source()->at(index.row());
  }

  Qt::ItemFlags flags(const QModelIndex& index) const override {
    return index.isValid() ? ListModelBase::flags(index) | Qt::ItemIsEditable : ListModelBase::flags(index);
  }

  // Editing goes through the source: the change is announced like any other, and a refused edit changes nothing.
  bool setData(const QModelIndex& index, const QVariant& value, int role = Qt::EditRole) override {
    bool isInt = false;
    const int edited = value.toInt(&isInt);
    return index.isValid() && role == Qt::EditRole && isInt && source()->replace(index.row(), edited);
  }
};

}  // namespace qt_cpp_test
