---
name: reflect-dont-hand-write
description: Use when writing or editing C++26 that maps enum values to names or names to enum values, parses command-line flags or keywords, builds or reads a JSON object field by field, or keeps a table or count in step with an enum or struct. Replaces text that repeats a type definition with code derived from the type by std::meta reflection. Trigger phrases - switch returning strings, enum to string, name table, string to enum, parse flags, serialize struct, add a field, add an enumerator, handler table, route table, GCC 16 reflection.
allowed-tools: Bash, Read, Grep, Edit
---

# Reflect, do not hand-write what a definition already says

A string that repeats an enumerator or a member name is a second copy that nothing keeps in step. Add an enumerator, forget the switch, and the compiler stays quiet. With reflection the type is the only copy.

## Derive, do not copy

| Hand-written | Derived |
|---|---|
| `switch (e) { case E::a: return "a"; ... }` or a ternary chain | `enum_name(e)`: `template for` over `std::define_static_array(std::meta::enumerators_of(^^E))`, return `std::meta::identifier_of(e)` |
| `{"a", E::a}, {"b", E::b}, ...` and a lookup over it | `enum_from_name<E>(word)`: the same loop, compare `word == identifier_of(e)`, return `[:e:]` |
| `if (w == "--json") ... else if (w == "--dry-run") ...` | annotate the members (`[[= flag("--json")]] bool as_json;`), walk `nonstatic_data_members_of` with `annotations_of_with_type` |
| `{"input", s.input}, {"output", s.output}, ...` or a `std::format` template that spells JSON keys | walk the aggregate: the key is `identifier_of(member)`, the value `object.[:member:]` |
| `static_cast<E>(n % 5)`, a count or `static_assert(sizeof...)` kept beside an enum | `std::meta::enumerators_of(^^E).size()` |
| `{E::a, &fn_a}, {E::b, &fn_b}` | annotate each handler with its enumerator, dispatch with `this->[:member:](...)`, `static_assert` that every enumerator is handled |

`references/reflect.hpp` is a self-contained, GCC 16.2 tested implementation of `enum_name`, `enum_from_name`, `enum_count`, `enum_values`, `unique_values`, annotation lookup, an aggregate member walk and an annotation-driven flag parser. Copy what you need or write the project's own; if the project already has helpers, use them (the `helpers` map in `.claude/cpp26-guard.json` makes the hook name them). Worked patterns: `references/patterns.md`.

## How to apply it

1. Name enumerators and members exactly as they appear on the wire (`message_start`, `cache_read`).
2. When the wire name cannot be an identifier (`--dry-run`, `x-api-key`), put it in an annotation on the member, not in a second table.
3. Keep the function `constexpr` so compile-time checks still cover it.
4. Test without naming cases: iterate the enumerators and assert the round trip, so a new enumerator is covered without editing the test.

## Before relying on a reflection feature

Reflection posts are mostly written for other compilers. `references/gcc-16.2-evidence.md` lists what GCC 16.2 with `-std=c++26 -freflection` accepts and rejects, each row backed by a probe under `tests/probes/`. Short list of traps: `annotation_of_type` does not exist (use `annotations_of_with_type`), annotation payloads must be structural (`char text[N]`, not `std::string_view`), `define_static_string` takes a `string_view`, iterate `define_static_array(...)` rather than the raw vector, call a spliced member as `this->[:m:](...)`.

## When a hand-written table is right

Only when the text is not an identifier of the type: an HTTP status phrase, a header name a protocol fixes, a value that differs from the enumerator on purpose, or a function-pointer table the language cannot annotate. Then add a line to the allowance file (`path|rule|text fragment|reason`). A reason starting `pending:` is debt to remove; a line whose finding disappeared fails `--strict` as `stale-allowance`.

## Checks

- `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/reflection_lint.py" --strict` scans the configured roots and fails on a new hand-written mirror and on a stale allowance. Rules and false-positive notes: the plugin README.
- A PreToolUse hook scans the text you are about to write and a PostToolUse hook the whole file afterwards. Both are advisory and never block.
