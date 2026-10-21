// A run is one change, an edit goes through the source, and a model asserts that it lives in its source's thread.
#include "check.hpp"
#include "list_model.hpp"

#include <qt_cpp/model_contract.hpp>

#include <QtCore/QCoreApplication>
#include <QtCore/QThread>
#include <QtTest/QSignalSpy>

#include <csignal>
#include <cstdio>
#include <sys/wait.h>
#include <unistd.h>

namespace {
using qt_cpp_test::IntListModel;
using qt_cpp_test::ObservableList;

constexpr int kRunLength = 5;

void range_is_one_change() {
  ObservableList<int> list;
  IntListModel model(&list);
  QSignalSpy aboutToInsert(&model, &QAbstractItemModel::rowsAboutToBeInserted);
  QSignalSpy inserted(&model, &QAbstractItemModel::rowsInserted);
  QSignalSpy aboutToRemove(&model, &QAbstractItemModel::rowsAboutToBeRemoved);
  QSignalSpy removed(&model, &QAbstractItemModel::rowsRemoved);
  qt_cpp::contract::ModelWatcher watcher(&model);

  CHECK(list.insertRange(0, QList<int>{10, 11, 12, 13, 14}));
  watcher.check();
  CHECK(aboutToInsert.count() == 1 && inserted.count() == 1);
  CHECK(inserted.first().at(1).toInt() == 0 && inserted.first().at(2).toInt() == kRunLength - 1);
  CHECK(model.rowCount() == kRunLength);

  CHECK(list.removeRange(1, 3));
  watcher.check();
  CHECK(aboutToRemove.count() == 1 && removed.count() == 1);
  CHECK(model.rowCount() == 2);
  CHECK(model.index(1, 0).data().toInt() == 14);
  CHECK(watcher.clean());

  CHECK(!list.removeRange(1, 5));  // refused: nothing announced
  CHECK(removed.count() == 1);
}

void edit_goes_through_the_source() {
  ObservableList<int> list;
  IntListModel model(&list);
  list.insert(0, 1);
  QSignalSpy changed(&model, &QAbstractItemModel::dataChanged);
  const QModelIndex row = model.index(0, 0);

  CHECK(model.flags(row) & Qt::ItemIsEditable);
  CHECK(model.setData(row, 42));
  CHECK(list.at(0) == 42);
  CHECK(changed.count() == 1);  // announced by the source, like any other change

  CHECK(!model.setData(row, QStringLiteral("not a number")));  // a refused edit changes nothing
  CHECK(!model.setData(model.index(5, 0), 1));
  CHECK(!model.setData(row, 7, Qt::DisplayRole));
  CHECK(list.at(0) == 42);
  CHECK(changed.count() == 1);
}

#ifndef QT_NO_DEBUG
// Runs `scenario` in a child process and reports whether it died of an assertion (SIGABRT).
template <class F>
bool aborts(F&& scenario) {
  std::fflush(nullptr);
  const pid_t child = fork();
  if (child == 0) {
    if (!std::freopen("/dev/null", "w", stderr)) _exit(2);
    scenario();
    _exit(0);
  }
  int status = 0;
  waitpid(child, &status, 0);
  return WIFSIGNALED(status) && WTERMSIG(status) == SIGABRT;
}

void one_thread_rule() {
  CHECK(!aborts([] {  // the control: same thread, no assertion
    ObservableList<int> list;
    IntListModel model(&list);
    list.insert(0, 1);
  }));
  CHECK(aborts([] {  // a model made in another thread than its source
    ObservableList<int> list;
    QThread other;
    list.moveToThread(&other);
    IntListModel model(&list);
  }));
}
#else
void one_thread_rule() { std::puts("SKIP the one-thread assertion (QT_NO_DEBUG: Q_ASSERT_X is compiled out)"); }
#endif

// Values whose move cannot throw are accepted; the one that can is refused by reject/throwing_move.cpp.
struct NothrowMove {
  NothrowMove() = default;
  NothrowMove(NothrowMove&&) noexcept = default;
  NothrowMove& operator=(NothrowMove&&) noexcept = default;
  NothrowMove(const NothrowMove&) = default;
  NothrowMove& operator=(const NothrowMove&) = default;
};
[[maybe_unused]] ObservableList<NothrowMove> accepted;
}  // namespace

int main(int argc, char** argv) {
  QCoreApplication app(argc, argv);
  range_is_one_change();
  edit_goes_through_the_source();
  one_thread_rule();
  return qt_cpp_test::finish("list_ranges_and_edits");
}
