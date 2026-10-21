// The checks must catch a wrong adapter. Each adapter in flawed_models.hpp has one mistake of the kind that makes
// ghost rows, and the same random driver must report it. The same driver reports nothing for the right adapter,
// so a detection is not noise. Control runs stop at the first violation: a wrong adapter leaves Qt's own
// bookkeeping unbalanced and a longer run would crash.
#include "check.hpp"
#include "flawed_models.hpp"
#include "list_model.hpp"

#include <qt_cpp/model_contract.hpp>

#include <QtCore/QCoreApplication>

#include <cstdio>

namespace {
constexpr int kSteps = 600;
constexpr unsigned kSeed = 11;
constexpr qt_cpp_test::Flaw kFlaws[] = {
    qt_cpp_test::Flaw::forgot_end_insert,
    qt_cpp_test::Flaw::wrong_row_remove,
    qt_cpp_test::Flaw::silent_replace,
    qt_cpp_test::Flaw::row_as_key,
};

qt_cpp::contract::Report run(qt_cpp_test::Flaw flaw, std::optional<int> stableKeyRole = std::nullopt, bool withMirror = true) {
  return qt_cpp::contract::run_random<qt_cpp_test::ObservableList<int>>(
      {.seed = kSeed, .steps = kSteps, .with_mirror = withMirror, .stop_at_first_violation = true, .with_proxy = withMirror, .stable_key_role = stableKeyRole},
      [flaw](qt_cpp_test::ObservableList<int>* source) { return std::make_unique<qt_cpp_test::FlawedListModel>(source, flaw); });
}

void print(const char* name, const qt_cpp::contract::Report& report) {
  std::printf("%-22s mismatches %d, violations %lld  first: %s\n", name, report.mismatches, static_cast<long long>(report.violations.size()),
              report.violations.isEmpty() ? "-" : qPrintable(report.violations.first()));
  std::fflush(stdout);
}
}  // namespace

int main(int argc, char** argv) {
  QCoreApplication app(argc, argv);
  using qt_cpp_test::Flaw;

  const auto right = run(Flaw::none);
  print("none (the right model)", right);
  CHECK(right.clean());

  for (const Flaw flaw : kFlaws) {
    const auto report = run(flaw);
    print(qt_cpp_test::name_of(flaw), report);
    CHECK(!report.clean());
  }

  // A row used as a key is also caught the way a sorting proxy would suffer from it: a mirror that caches the
  // role the model promises is stable sees the value shift under an insert with no signal.
  const auto asKey = run(Flaw::row_as_key, Qt::UserRole);
  print("row_as_key (mirror)", asKey);
  CHECK(!asKey.violations.isEmpty());
  // A value that changes with no dataChanged is invisible to every check on the model's own data (the model reads
  // its source live, so it is always right about itself): with the mirror off the run is clean, with it on it is not.
  CHECK(run(Flaw::silent_replace, std::nullopt, false).clean());
  CHECK(!run(Flaw::silent_replace).clean());
  // The same promise kept by the right model is a different matter: it offers no such role, and the driver says so.
  CHECK(run(Flaw::none).violations.isEmpty());
  return qt_cpp_test::finish("contract_flaws_detected");
}
