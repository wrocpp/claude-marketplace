# GCC 16.2 reflection evidence

Compiler: GCC 16.2.0 (Homebrew on macOS, official `gcc:16` image on Linux). Flags: `-std=c++26 -freflection -fsyntax-only`. Every row names its probe under `tests/probes/`; `sh tests/run.sh` re-checks all of them, and a probe in `absent/` must fail to compile, so the day a compiler accepts it the run reports that the finding is out of date.

Apple clang cannot compile `<meta>`; clang forks implement a different API surface. Treat reflection blog posts as a source of ideas, not of spellings.

## Works (`probes/supported/`)

| Do | Probe |
|---|---|
| Annotate members and test with `std::meta::annotations_of_with_type(m, ^^A).empty()` | `annotations_on_members.cpp` |
| Annotate enumerators, same query | `annotations_on_enumerators.cpp` |
| Payload as `char text[N]` filled by a consteval factory | `annotation_with_char_array.cpp` |
| Payload as `char const*` made by `std::define_static_string(std::string_view)` | `annotation_with_pointer_from_static_string.cpp`, `define_static_string_from_string_view.cpp` |
| `std::define_static_array(enumerators_of(^^E))` then `template for` and `[:e:]` | `enum_from_name_by_template_for.cpp` |
| `enumerators_of(^^E).size()` as the count; pairwise `extract<E>` comparison to detect alias enumerators | `enumerator_count_and_alias_detection.cpp` |
| `identifier_of(e)` as a null-terminated `string_view` | `identifier_of_is_null_terminated.cpp` |
| `std::string{identifier}` from a reflected name, at run time and in a constant expression | `std_string_from_reflected_name.cpp` |
| `access_context::unchecked()` for private members, `unprivileged()` for public only | `access_contexts.cpp` |
| `subobjects_of` includes bases; `nonstatic_data_members_of` skips them | `subobjects_of_includes_bases.cpp` |
| `is_aggregate_type`, `is_enumerable_type` queries | `aggregate_and_enumerable_queries.cpp` |
| Write members through a splice in a constant expression: `s.[:m:] = n++` | `write_members_by_splice.cpp` |
| `this->[:member:]()` over annotated member functions | `annotated_member_function_dispatch.cpp` |
| `define_aggregate` from a `consteval {}` block in a class template | `define_aggregate_from_consteval_block.cpp` |
| An aggregate `std::formatter<T>` built with `template for` and `std::format_to` | `formatter_for_aggregates.cpp` |
| `std::meta::current_function()` as a template default argument | `current_function_as_template_default.cpp` |
| The same default walked with `parent_of` as a compile-time caller check, reported by a `static_assert` | `caller_namespace_guard.cpp` |
| `#embed` into a `constexpr char[]` parsed at compile time | `embed_into_constexpr_array.cpp` |

## Does not work (`probes/absent/`)

| Do not | Why | Probe |
|---|---|---|
| `std::meta::annotation_of_type<A>(m)` | not a member of `std::meta`; use `annotations_of_with_type` | `annotation_of_type.cpp` |
| An annotation payload with a `std::string_view` member | "annotation does not have structural type" | `annotation_with_string_view_member.cpp` |
| `std::define_static_string(char const*)` | no matching function; pass a `string_view` | `define_static_string_from_char_pointer.cpp` |
| `template for` over the raw `std::vector<info>` of `enumerators_of` | not a constant expression (it refers to `operator new`); wrap in `define_static_array` | `template_for_over_raw_vector.cpp` |
| `(this->*[:m:])()` to call a spliced member function | "cannot implicitly reference a class member through a splice" | `member_pointer_splice_call.cpp` |
| `std::format` in a constant expression | non-constexpr function (`__cpp_lib_constexpr_format` is undefined); build constexpr text with explicit appends | `constexpr_std_format.cpp` |
| Calling a restricted function from another layer | rejected by design: the `static_assert` names the offending caller | `caller_namespace_guard_rejects_other_layers.cpp` |

## Reported, not probed here

Observed by the author in a larger C++26 project on GCC 16.2 with modules; a single-file probe cannot show them, so treat them as leads and re-check in your tree.

- `display_string_of(^^T)` text is implementation-defined (for a module-attached entity it carried an `@module` suffix); never parse it.
- A constexpr function in one module that returns `std::optional<T>` of a module type, called at run time from another translation unit, can leave `optional<T>::operator*` undefined at link time; an explicit instantiation `template class std::optional<T>;` at the end of the defining module fixed it.
- An inline function with contracts exported from a module left `__tu_has_violation` undefined at link time; contracts on a non-inline declaration with the body in an implementation unit linked.
- libstdc++ 16.2 has no default `handle_contract_violation`; the program must define one.
- A `std::string` built from a reflected name inside a constant expression did not compile under the ASan flags; compile-time-only targets were built with `-fno-sanitize=all`.
- `std::add_sat` was not exported by `import std`.
