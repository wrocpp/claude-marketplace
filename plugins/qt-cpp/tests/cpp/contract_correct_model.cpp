// The right list model passes the whole contract: view mirror from signals only, QAbstractItemModelTester in
// Fatal mode, selection and persistent-index survival, and a sorting proxy with a second mirror, under seeded
// random changes against a plain reference. A model that passes is not noise: contract_flaws_detected.cpp runs the
// same driver on adapters that must fail.
#include "check.hpp"
#include "list_model.hpp"

#include <qt_cpp/model_contract.hpp>

#include <QtCore/QCoreApplication>

#include <cstdio>

namespace {
constexpr unsigned kSeeds[] = {1, 2, 3, 4};
constexpr int kSteps = 4000;
constexpr int kMinAppliedPercent = 30;  // of all steps (a step may also select a row, or be refused)
}  // namespace

int main(int argc, char** argv) {
  QCoreApplication app(argc, argv);
  using namespace qt_cpp_test;
  int steps = 0;
  for (const unsigned seed : kSeeds) {
    const auto report = qt_cpp::contract::run_random<ObservableList<int>>(
        {.seed = seed, .steps = kSteps, .with_proxy = true, .with_tester = true},
        [](ObservableList<int>* source) { return std::make_unique<IntListModel>(source); });
    std::printf("seed %u: %d steps, %d applied, %d refused, mismatches %d, violations %lld\n", seed, report.steps, report.applied,
                report.refused, report.mismatches, static_cast<long long>(report.violations.size()));
    CHECK(report.clean());
    CHECK(report.applied * 100 > report.steps * kMinAppliedPercent);  // the run changed the model often
    CHECK(report.refused > 0);                 // and asked for invalid rows now and then
    steps += report.steps;
  }
  std::printf("%d changes in all\n", steps);
  return finish("contract_correct_model");
}
