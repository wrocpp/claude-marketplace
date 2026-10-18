#include <contracts>
#include <cstdlib>

void handle_contract_violation(std::contracts::contract_violation const&) {
  std::abort();
}
