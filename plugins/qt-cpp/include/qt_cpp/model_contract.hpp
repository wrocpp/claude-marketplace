// A contract test for a list model: what a view would believe, kept from the model's signals only, and a seeded
// random driver that compares the model, the view mirror, a selection, a persistent index and a sorting proxy with a
// plain reference after every change.
//
// A ghost row is a row that a view shows and the model no longer has (or the reverse). A view only learns about
// changes from signals, so ModelWatcher is built from the signals alone and compared with the live model after every
// step. A change that was not announced, announced with the wrong rows, announced in the wrong order or never
// confirmed shows up as a difference. A check on the model's own data cannot see that: the model reads its container
// live, so it is always right about itself.
//
// The driver works on a *source*: any object with
//     qsizetype size() const;
//     bool insert(int row, int value);   bool remove(int row);     bool replace(int row, int value);
//     bool move(int from, int to);       bool clear();
// where each call returns false and changes nothing when the request is invalid (row out of range, from == to, an
// empty container to clear), and `move` leaves the entry at row `to`. The model shows `value` as Qt::DisplayRole.
#pragma once

#include <QtCore/QAbstractItemModel>
#include <QtCore/QItemSelectionModel>
#include <QtCore/QPersistentModelIndex>
#include <QtCore/QSet>
#include <QtCore/QSortFilterProxyModel>
#include <QtCore/QString>
#include <QtCore/QStringList>
#include <QtTest/QAbstractItemModelTester>

#include <algorithm>
#include <memory>
#include <optional>
#include <random>
#include <utility>
#include <vector>

namespace qt_cpp::contract {

constexpr int kIndexSlack = 2;      // a row is drawn from [-1, size + kIndexSlack), so some requests are invalid
constexpr int kChangeKinds = 100;   // the weights below add up to this
constexpr int kWeightInsert = 30;
constexpr int kWeightRemove = 25;
constexpr int kWeightReplace = 15;
constexpr int kWeightMove = 14;
constexpr int kWeightSelect = 14;   // the rest is clear
constexpr int kFirstRole = Qt::UserRole;

// What a view believes about one row, kept from the model's signals only.
struct MirrorRow {
  QVariant key;
  QVariant display;
  bool operator==(const MirrorRow&) const = default;
};

class ModelWatcher : public QObject {
 public:
  // `stableKeyRole` names a role the model promises to be a stable identity of its entries; the mirror then caches
  // it, so a value that shifts with no signal (the row used as a key) is reported. A list offers no such role.
  explicit ModelWatcher(QAbstractItemModel* model, std::optional<int> stableKeyRole = std::nullopt)
      : QObject(model), m_model(model), m_keyRole(stableKeyRole) {
    m_rows = readAll();
    m_announcedCount = m_model->rowCount();
    using M = QAbstractItemModel;
    connect(model, &M::rowsAboutToBeInserted, this, [this](const QModelIndex&, int first, int last) { begin(Open::insert, first, last); });
    connect(model, &M::rowsInserted, this, [this](const QModelIndex&, int first, int last) {
      if (end(Open::insert, first, last, m_countBefore + (last - first + 1)))
        for (int row = first; row <= last; ++row) m_rows.insert(m_rows.begin() + row, read(row));
    });
    connect(model, &M::rowsAboutToBeRemoved, this, [this](const QModelIndex&, int first, int last) { begin(Open::remove, first, last); });
    connect(model, &M::rowsRemoved, this, [this](const QModelIndex&, int first, int last) {
      if (end(Open::remove, first, last, m_countBefore - (last - first + 1)) && last < static_cast<int>(m_rows.size()))
        m_rows.erase(m_rows.begin() + first, m_rows.begin() + last + 1);
    });
    connect(model, &M::rowsAboutToBeMoved, this, [this](const QModelIndex&, int first, int last, const QModelIndex&, int destination) {
      begin(Open::move, first, last);
      m_moveDestination = destination;
    });
    connect(model, &M::rowsMoved, this, [this](const QModelIndex&, int first, int last, const QModelIndex&, int destination) {
      if (end(Open::move, first, last, m_countBefore)) applyMove(first, last, destination);
    });
    connect(model, &M::modelAboutToBeReset, this, [this] { begin(Open::reset, 0, 0); });
    connect(model, &M::modelReset, this, [this] {
      if (m_open != Open::reset) violation("modelReset without modelAboutToBeReset");
      m_open = Open::none;
      reload();
    });
    // A proxy that re-sorts after a value changed says so with layoutChanged; a view then reads every row again.
    connect(model, &M::layoutChanged, this, [this] { reload(); });
    connect(model, &M::dataChanged, this, [this](const QModelIndex& top, const QModelIndex& bottom) {
      for (int row = top.row(); row <= bottom.row() && row < static_cast<int>(m_rows.size()); ++row) m_rows[row] = read(row);
    });
  }

  // Call after every change: the change must be closed, and the mirror must equal the live model.
  void check() {
    if (m_open != Open::none) violation("a change was announced and never confirmed");
    if (m_model->rowCount() != m_announcedCount) violation("the row count changed without an announcement");
    const std::vector<MirrorRow> live = readAll();
    if (m_rows.size() != live.size()) {
      violation(QStringLiteral("a view would show %1 rows, the model has %2").arg(m_rows.size()).arg(live.size()));
      return;
    }
    for (std::size_t row = 0; row < live.size(); ++row) {
      if (m_rows[row] == live[row]) continue;
      violation(QStringLiteral("row %1: a view would show key %2 and %3, the model has key %4 and %5")
                    .arg(row).arg(m_rows[row].key.toString(), m_rows[row].display.toString(), live[row].key.toString(), live[row].display.toString()));
      return;
    }
  }

  const QStringList& violations() const { return m_violations; }
  bool clean() const { return m_violations.isEmpty(); }

 private:
  enum class Open { none, insert, remove, move, reset };

  MirrorRow read(int row) const {
    const QModelIndex index = m_model->index(row, 0);
    return {m_keyRole ? m_model->data(index, *m_keyRole) : QVariant(), m_model->data(index, Qt::DisplayRole)};
  }
  std::vector<MirrorRow> readAll() const {
    std::vector<MirrorRow> out;
    for (int row = 0; row < m_model->rowCount(); ++row) out.push_back(read(row));
    return out;
  }
  void reload() {
    m_rows = readAll();
    m_announcedCount = m_model->rowCount();
  }
  void applyMove(int first, int last, int destination) {
    if (destination != m_moveDestination) violation("rowsMoved destination differs from rowsAboutToBeMoved");
    const int count = last - first + 1;
    const std::vector<MirrorRow> block(m_rows.begin() + first, m_rows.begin() + last + 1);
    m_rows.erase(m_rows.begin() + first, m_rows.begin() + last + 1);
    const int at = destination > last ? destination - count : destination;
    m_rows.insert(m_rows.begin() + at, block.begin(), block.end());
  }
  void violation(const QString& text) { m_violations.append(text); }
  void begin(Open kind, int first, int last) {
    if (m_open != Open::none) violation("a change was announced while another was still open");
    m_open = kind;
    m_first = first;
    m_last = last;
    m_countBefore = m_model->rowCount();
  }
  // Returns true when the confirmation matches the announcement and the row count is what the change implies.
  bool end(Open kind, int first, int last, int expectedCount) {
    bool ok = true;
    if (m_open != kind) {
      violation("a change was confirmed that was not announced");
      ok = false;
    }
    if (first != m_first || last != m_last) {
      violation("the confirmation names other rows than the announcement");
      ok = false;
    }
    if (m_model->rowCount() != expectedCount) {
      violation("the row count after the change is not what the change implies");
      ok = false;
    }
    m_open = Open::none;
    m_announcedCount = m_model->rowCount();
    return ok;
  }

  QAbstractItemModel* m_model;
  std::optional<int> m_keyRole;
  std::vector<MirrorRow> m_rows;
  QStringList m_violations;
  Open m_open = Open::none;
  int m_first = 0;
  int m_last = 0;
  int m_countBefore = 0;
  int m_moveDestination = 0;
  int m_announcedCount = 0;
};

// The expected rows, in model order, with an id per entry that never changes while it lives.
class Reference {
 public:
  struct Row {
    int value;
    int id;
  };

  const std::vector<Row>& rows() const { return m_rows; }
  int size() const { return static_cast<int>(m_rows.size()); }
  bool valid(int row) const { return row >= 0 && row < size(); }

  bool insert(int row, int value) {
    if (row < 0 || row > size()) return false;
    m_rows.insert(m_rows.begin() + row, Row{value, m_nextId++});
    return true;
  }
  bool remove(int row) {
    if (!valid(row)) return false;
    m_rows.erase(m_rows.begin() + row);
    return true;
  }
  bool replace(int row, int value) {
    if (!valid(row)) return false;
    m_rows[static_cast<std::size_t>(row)].value = value;
    return true;
  }
  bool move(int from, int to) {
    if (!valid(from) || !valid(to) || from == to) return false;
    const Row moved = m_rows[static_cast<std::size_t>(from)];
    m_rows.erase(m_rows.begin() + from);
    m_rows.insert(m_rows.begin() + to, moved);
    return true;
  }
  bool clear() {
    if (m_rows.empty()) return false;
    m_rows.clear();
    return true;
  }

 private:
  std::vector<Row> m_rows;
  int m_nextId = 0;
};

struct Report {
  int steps = 0;
  int applied = 0;          // changes the source accepted
  int refused = 0;          // invalid requests the source refused
  int mismatches = 0;       // the model, the source, the selection or the proxy disagreed with the reference
  QStringList violations;   // from the ModelWatchers
  bool clean() const { return mismatches == 0 && violations.isEmpty(); }
};

struct Options {
  unsigned seed = 1;
  int steps = 1000;
  // Compare the view mirror with the model after every step. Off, only the checks on the model's own data run:
  // that is the control that shows what the mirror adds.
  bool with_mirror = true;
  // After a wrong adapter Qt's own bookkeeping can be unbalanced and crash, so a control run stops where the
  // fault first shows.
  bool stop_at_first_violation = false;
  // A QSortFilterProxyModel sorted by display value on top of the model, with a second mirror.
  bool with_proxy = false;
  // QAbstractItemModelTester in Fatal mode: it aborts on a wrong model, so a control run leaves it off.
  bool with_tester = false;
  // A role the model promises is a stable identity of an entry. None: the model offers no key role, and the
  // driver asserts that Qt::UserRole is empty (a list's only identity is its row, which shifts without a signal).
  std::optional<int> stable_key_role = std::nullopt;
};

// One run: the source, the model and the reference, and the checks made after every step.
template <class Source, class MakeModel>
class Run {
 public:
  Run(const Options& options, MakeModel& makeModel) : m_options(options), m_rng(options.seed), m_model(makeModel(&m_source)) {
    m_watcher = std::make_unique<ModelWatcher>(m_model.get(), options.stable_key_role);
    m_selection = std::make_unique<QItemSelectionModel>(m_model.get());
    if (options.with_tester)
      m_tester = std::make_unique<QAbstractItemModelTester>(m_model.get(), QAbstractItemModelTester::FailureReportingMode::Fatal);
    if (options.with_proxy) makeProxy();
  }

  Report execute() {
    for (int step = 0; step < m_options.steps; ++step) {
      ++m_report.steps;
      applyRandomChange();
      if (!verifyStep()) break;
    }
    m_report.violations = m_watcher->violations();
    if (m_proxyWatcher) m_report.violations += m_proxyWatcher->violations();
    return m_report;
  }

 private:
  int draw(int low, int high) { return std::uniform_int_distribution<int>(low, high - 1)(m_rng); }
  void expect(bool ok) { m_report.mismatches += ok ? 0 : 1; }
  int randomRow() { return draw(-1, m_reference.size() + kIndexSlack); }

  void makeProxy() {
    m_proxy = std::make_unique<QSortFilterProxyModel>();
    m_proxy->setSortRole(Qt::DisplayRole);
    m_proxy->setSourceModel(m_model.get());
    m_proxy->sort(0);
    m_proxyWatcher = std::make_unique<ModelWatcher>(m_proxy.get(), m_options.stable_key_role);
  }

  void applyRandomChange() {
    const int kind = draw(0, kChangeKinds);
    const int row = randomRow();
    const int value = m_nextValue++;
    bool accepted = false;
    bool changed = true;
    if (kind < kWeightInsert) {
      accepted = apply(m_reference.insert(row, value), m_source.insert(row, value));
    } else if (kind < kWeightInsert + kWeightRemove) {
      accepted = removeRow(row);
    } else if (kind < kWeightInsert + kWeightRemove + kWeightReplace) {
      accepted = apply(m_reference.replace(row, value), m_source.replace(row, value));
    } else if (kind < kWeightInsert + kWeightRemove + kWeightReplace + kWeightMove) {
      const int to = randomRow();
      accepted = apply(m_reference.move(row, to), m_source.move(row, to));
    } else if (kind < kWeightInsert + kWeightRemove + kWeightReplace + kWeightMove + kWeightSelect) {
      changed = false;
      selectRandomRow();
    } else {
      accepted = clearAll();
    }
    if (changed) ++(accepted ? m_report.applied : m_report.refused);
  }

  // The reference and the source must accept or refuse the same request.
  bool apply(bool expected, bool actual) {
    expect(actual == expected);
    return actual;
  }

  bool removeRow(int row) {
    const std::optional<int> id = m_reference.valid(row) ? std::optional<int>(m_reference.rows()[static_cast<std::size_t>(row)].id) : std::nullopt;
    const bool accepted = apply(m_reference.remove(row), m_source.remove(row));
    if (accepted && id) m_selectedIds.remove(*id);
    if (accepted && id && m_trackedId == id) m_trackedId.reset();
    return accepted;
  }

  bool clearAll() {
    const bool accepted = apply(m_reference.clear(), m_source.clear());
    if (accepted) {
      m_selectedIds.clear();
      m_trackedId.reset();
    }
    return accepted;
  }

  void selectRandomRow() {
    if (m_reference.rows().empty()) return;
    const int row = draw(0, m_reference.size());
    const int id = m_reference.rows()[static_cast<std::size_t>(row)].id;
    m_selection->select(m_model->index(row, 0), QItemSelectionModel::Toggle | QItemSelectionModel::Rows);
    if (!m_selectedIds.remove(id)) m_selectedIds.insert(id);
    m_tracked = m_model->index(row, 0);
    m_trackedId = id;
  }

  // Returns false when a control run should stop.
  bool verifyStep() {
    if (m_options.with_mirror) m_watcher->check();
    if (m_options.stop_at_first_violation && !m_watcher->clean()) return false;
    if (m_proxy) {
      if (m_options.with_mirror) m_proxyWatcher->check();
      if (m_options.stop_at_first_violation && !m_proxyWatcher->clean()) return false;
      verifyProxy();
    }
    expect(m_source.size() == static_cast<qsizetype>(m_reference.size()));
    verifyModelRows();
    verifySelection();
    verifyPersistentIndex();
    return true;
  }

  void verifyProxy() {
    std::vector<Reference::Row> sorted = m_reference.rows();
    std::stable_sort(sorted.begin(), sorted.end(), [](const auto& a, const auto& b) { return a.value < b.value; });
    expect(m_proxy->rowCount() == static_cast<int>(sorted.size()));
    for (int row = 0; row < m_proxy->rowCount() && row < static_cast<int>(sorted.size()); ++row)
      expect(m_proxy->index(row, 0).data(Qt::DisplayRole).toInt() == sorted[static_cast<std::size_t>(row)].value);
  }

  void verifyModelRows() {
    expect(m_model->rowCount() == m_reference.size());
    for (int row = 0; row < m_model->rowCount() && row < m_reference.size(); ++row) {
      const QModelIndex index = m_model->index(row, 0);
      expect(m_model->data(index, Qt::DisplayRole).toInt() == m_reference.rows()[static_cast<std::size_t>(row)].value);
      if (!m_options.stable_key_role) expect(!m_model->data(index, kFirstRole).isValid());
    }
    // A list has no children: a valid parent has no rows.
    if (m_model->rowCount() > 0) expect(m_model->rowCount(m_model->index(0, 0)) == 0);
  }

  void verifySelection() {
    QSet<int> selectedRows;
    for (const QModelIndex& index : m_selection->selectedRows()) selectedRows.insert(index.row());
    QSet<int> expectedRows;
    for (int row = 0; row < m_reference.size(); ++row)
      if (m_selectedIds.contains(m_reference.rows()[static_cast<std::size_t>(row)].id)) expectedRows.insert(row);
    expect(selectedRows == expectedRows);
  }

  // A persistent index follows its entry, and is invalid once the entry is gone.
  void verifyPersistentIndex() {
    if (!m_trackedId) {
      expect(!m_tracked.isValid());
      return;
    }
    const auto at = std::find_if(m_reference.rows().begin(), m_reference.rows().end(), [&](const Reference::Row& r) { return r.id == *m_trackedId; });
    expect(at != m_reference.rows().end() && m_tracked.isValid() && m_tracked.row() == at - m_reference.rows().begin());
  }

  Options m_options;
  std::mt19937 m_rng;
  Source m_source;
  std::unique_ptr<QAbstractItemModel> m_model;
  std::unique_ptr<ModelWatcher> m_watcher;
  std::unique_ptr<QItemSelectionModel> m_selection;
  std::unique_ptr<QAbstractItemModelTester> m_tester;
  std::unique_ptr<QSortFilterProxyModel> m_proxy;
  std::unique_ptr<ModelWatcher> m_proxyWatcher;
  QPersistentModelIndex m_tracked;
  std::optional<int> m_trackedId;
  QSet<int> m_selectedIds;
  Reference m_reference;
  Report m_report;
  int m_nextValue = 1;
};

// Applies `options.steps` random changes to a default-constructed Source, with the model that `makeModel(Source*)`
// returns (a std::unique_ptr<QAbstractItemModel>), and compares everything with the reference after each one.
template <class Source, class MakeModel>
Report run_random(const Options& options, MakeModel&& makeModel) {
  Run<Source, MakeModel> run(options, makeModel);
  return run.execute();
}

}  // namespace qt_cpp::contract
