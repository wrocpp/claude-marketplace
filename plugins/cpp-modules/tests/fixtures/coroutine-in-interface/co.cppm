export module co;
import std;

export struct task {
  struct promise_type {
    task get_return_object() { return {}; }
    std::suspend_never initial_suspend() noexcept { return {}; }
    std::suspend_never final_suspend() noexcept { return {}; }
    void return_value(int) {}
    void unhandled_exception() {}
  };
};

export task answer() { co_return 42; }
