# The copy-smell scanner

`scripts/copy_scan.py` (stdlib Python). It masks comments and string literals, then matches patterns in the
code. It reports `line: [rule] message`.

| rule | fires on | fix |
|---|---|---|
| `param-const-ref` | `(... const std::string& s ...)`, or the same for `std::vector<T>`, `map`, `set`, `deque`, `list` and the unordered ones, as a parameter | `std::string_view`, `std::span<const T>` (a map or set has no view: keep the reference) |
| `sink-copy` | such a parameter that is stored: `member_(p)`, `member{p}` or `member_ = p;` in the same function | take it by value, `std::move` it |
| `range-for-copy` | `for (std::string s : xs)`, also `const` and the container types above, with no `&` | `const std::string&` |
| `substr-copy` | any `.substr(` | take a `string_view` first |
| `return-move` | `return std::move(x);` where `x` is declared as a local in the same text and is not named after `&&` | `return x;` |
| `view-of-temporary` | `std::string_view v = std::string(...)`, `std::to_string(`, `std::format(`, `std::vector<...>{`, `x.str()`; same for `std::span<...>` | keep the owner in a named variable |
| `view-return-temp` | a function returning `std::string_view` whose body returns `std::string(`, `std::to_string(` or `std::format(` | return `std::string` |
| `copy-from-name` | `std::string b = a;` (also the container types) | reference or view, unless it is an ownership boundary |
| `cstr-roundtrip` | `std::string(x.c_str())` | use `x` |
| `ref-capture-escape` | `std::thread t([&]...`, `std::jthread`, `std::async(... [&]`, and `.detach()` | capture by value or move |

## Silencing and configuring

- `// copy-ok: <reason>` on the line or the line above. The reason must contain a word; an empty marker is ignored.
- `.claude/cpp-conventions.json`: `{"copies": {"block": true}}` blocks (exit 2); `{"copies": {"disable": true}}` turns the scanner off.
- `CPP_CONVENTIONS_OFF=1` in the environment turns the hook off.

## What it does not catch

- Anything that needs types: `auto x = obj.name();` copying a string member, aliases (`using Str = std::string`),
  template parameters, overloads.
- A by-value parameter that is never moved, or a sink that is copied instead of moved in the body.
- A copy hidden behind a function return, or `std::function` captures that copy large objects.
- `shared_ptr<T>` that could be `shared_ptr<const T>`.
- A dangling view whose owner is not visible in the same text, and views stored in members.
- Edits: the hook sees only the new text of an `Edit`, so a rule that needs a declaration elsewhere
  (`return-move`, `sink-copy`) stays quiet when the declaration is not in the snippet.

For these use clang-tidy (`performance-*`, `bugprone-use-after-move`) via the separate `tidy-agent` plugin, and
build on GCC and Clang with `-Wall -Wextra`.
