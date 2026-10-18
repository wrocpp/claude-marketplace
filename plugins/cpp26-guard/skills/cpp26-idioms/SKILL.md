---
name: cpp26-idioms
description: Use when writing or editing C++26 - a new function, a template that takes a callback or stream, a new enum, formatting or building a string, printing, adding a check, including a header, or about to write a comment. Keeps new code in the C++26 style - concepts instead of bare template parameters, import std instead of standard includes in module projects, std::format and std::print instead of iostream and printf, one append instead of a chain, and (opt-in) no comments except marked exceptions. Trigger phrases - write C++, new template, add a callback, format a string, build a string, print, include a header, add a comment, constrain a template.
allowed-tools: Bash, Read, Grep, Edit
---

# C++26 idioms

`${CLAUDE_PLUGIN_ROOT}/scripts/cpp26_lint.py` enforces the rules below and a PreToolUse hook reads the text you are about to write and names the rule; its message is the replacement to apply. Names that repeat a type belong to the sibling skill `reflect-dont-hand-write`.

## Rules with the replacement

| Instead of | Write | Rule |
|---|---|---|
| `template <class F>` whose parameter is called, awaited or used as a stream or sink | `template <std::invocable<Args> F>`, a named concept, or a `requires` clause. A pure type utility (`T` only in `sizeof` or a trait) needs none | `unconstrained-template` |
| `#include <vector>`, `<string>`, `<format>` in a module-based project | `import std;`. C and POSIX headers, `<meta>` and `<contracts>` stay in the global module fragment | `std-include` (needs `"modules": true`) |
| `std::cout`, `printf`, `fprintf` | `std::println(stderr, "...", x)` or `std::print`; text with `std::format` | `legacy-io` |
| `out += a; out += b; out += c;` or three `push_back` calls in a row | run time: `std::format_to(std::back_inserter(out), ...)` or one `std::format`; constexpr code: one append per part (`std::format` is not constexpr on GCC 16.2); a container: a braced list or `std::ranges::to` | `append-chain` |
| `out += c == q ? std::string(1, c) : std::string{1, c};` or `out += "a" + name + "b"` | append each part once: `std::format_to`, or split on the special character and append each run | `string-temporary` |
| any comment | opt-in house style (`"rules": {"comment": true}`): nothing, because the name says it and a rule lives in a test, a requirement or the commit message; allowed are `// Exception: <reason>` on its own line and the `}  // namespace x` closer | `comment` |

Details, false positives and what each rule cannot see: `references/rules.md`.

## Habits no lint can check

1. **Add an enum** with the wire names as enumerators, then `static_assert` what must hold: a round trip over its enumerators and no alias values. Derive tables from the enum, never the enum from a table.
2. **Structural `static_assert`s** state a property of a type once (every member is `std::uint64_t`; a handler table has one entry per enumerator). Walk `nonstatic_data_members_of` rather than listing members.
3. **Contracts at API boundaries**: `pre`/`post` on the declaration, `contract_assert` inside bodies; `std::expected` for failures callers must handle, contracts for programmer errors. On GCC 16.2 an inline function with contracts exported from a module failed to link, so put the body in an implementation unit (re-check in your tree).
4. **`constexpr` by default**, with a `static_assert` beside it that exercises the function.
5. **Braced construction** (designated initializers for aggregates, an initializer list for containers) and **no needless copies** (`string_view` and `span` to borrow, sink parameters by value then `std::move`).
6. **Name every number once**; only `0`, `1` and `100%` stand bare.

## Use the compiler as the second opinion

The scanners read text, not compiler state, so a flagged line may be fine for your compiler and an unflagged one wrong. `references/rules.md` lists the GCC 16.2 limits that matter here (no constexpr `std::format`, `-freflection` flag, `<meta>` beside `import std`); probes are under `tests/probes/`.

## When a rule has a real exception

Add a justified line to the allowance file (`path|rule|text fragment|reason`, default `.claude/cpp26-guard-allow.txt`); under the comment policy a `// Exception: <reason>` line above the code also works. A reason starting `pending:` is debt to remove; a stale line fails `--strict`. Configuration (roots, modules, per-rule switches, helper names) lives in `.claude/cpp26-guard.json`; see the plugin README.
