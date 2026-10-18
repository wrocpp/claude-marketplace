# Reflection patterns

Every snippet builds on GCC 16.2 with `-std=c++26 -freflection`; the full versions are in `reflect.hpp` and are exercised by `tests/reference_selftest.cpp`. The probe that backs each primitive is named in `gcc-16.2-evidence.md`.

## Enumerators to names and back

```cpp
template <class E>
inline constexpr auto enumerators = std::define_static_array(std::meta::enumerators_of(^^E));

template <class E>
constexpr std::string_view enum_name(E const value) noexcept {
    template for (constexpr auto e : enumerators<E>) {
        if (value == [:e:]) {
            return std::meta::identifier_of(e);
        }
    }
    return {};
}
```

`identifier_of` returns a null-terminated `string_view`. `std::string{enum_name(v)}` works at run time and in constant expressions. The loop is a linear scan, fine for the dozens of enumerators a real enum has.

## Alias detection

`enum class E { a, b, c, d = c };` has four enumerators but three values. `enumerators_of(^^E).size()` counts names; compare `extract<E>` of each pair (`unique_values<E>()` in `reflect.hpp`) when a round trip must be exact, and `static_assert` it beside the enum.

## Annotations carry the wire name

```cpp
struct flag { char text[24]; };
consteval flag make_flag(std::string_view spelling);

struct options {
    [[= make_flag("--json")]] bool as_json = false;
    [[= make_flag("--dry-run")]] bool dry_run = false;
};
```

The payload must be a structural type: a `char[N]` filled by a consteval factory, or a `char const*` made by `std::define_static_string(std::string_view)`. A `std::string_view` member is rejected ("annotation does not have structural type"). Read it back with `std::meta::annotations_of_with_type(member, ^^flag)` and `std::meta::extract<flag>(...)`.

Walk the members with `template for` over `std::define_static_array(std::meta::nonstatic_data_members_of(^^T, std::meta::access_context::unprivileged()))`; use `unchecked()` to include private members, and `subobjects_of` when bases matter (`nonstatic_data_members_of` skips them).

## Aggregate to key/value without a table

```cpp
template <class T, class Visit>
    requires std::is_aggregate_v<T>
constexpr void for_each_member(T const& object, Visit&& visit) {
    template for (constexpr auto m : members<T>) {
        visit(std::meta::identifier_of(m), object.[:m:]);
    }
}
```

The member name is the key. Use an annotation for a key that cannot be an identifier. Reading a value back is the same walk with `object.[:m:] = ...`.

## Handlers bound to enumerators

```cpp
struct handles { kind which; };
struct machine {
    [[= handles{kind::a}]] constexpr void on_a();
    [[= handles{kind::b}]] constexpr void on_b();
    constexpr void accept(kind which);
};
```

`accept` walks `members_of(^^machine, ...)` filtered by `annotations_of_with_type(m, ^^handles)` and calls `this->[:m:]()` when the annotation equals `which`. Add a `static_assert` that every enumerator has exactly one handler. Probe: `annotated_member_function_dispatch.cpp`. Do not write `(this->*[:m:])()`: GCC rejects it with "cannot implicitly reference a class member through a splice".

## Types derived from a type

`std::meta::define_aggregate` inside a `consteval {}` block of a class template builds a struct with one member per enumerator (probe `define_aggregate_from_consteval_block.cpp`); an aggregate `std::formatter<T>` is a `template for` over the members (probe `formatter_for_aggregates.cpp`).

## What stays hand-written

A text that is not an identifier of the type; a function-pointer table the language cannot annotate; wire values that differ from the enumerator on purpose. Record each in the allowance file with its reason.
