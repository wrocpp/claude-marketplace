---
name: designated-init
description: Use BEFORE writing or reviewing C++ that builds an object's contents - a request, options or config struct, test arguments, headers, a map, a vector of fixtures. State the whole value in ONE braced expression (designated initializer for an aggregate, initializer list for a container), not default-construct then assign or push_back. Covers designator order, omitted members (silent on Apple clang), the C++20 requirement and the loop exception. Triggers - designated initializer, missing initializer for member, -Wmissing-field-initializers, build the request, fill in the options, push_back in a loop, compiles on Mac but not on gcc.
---

# Build a value in one braced expression

Write what an object contains in a single braced expression, at the point it is created.

```cpp
const Options options{.width = 80, .wrap = true};                 // aggregate: designated initializer
const std::map<std::string, int> ports{{"http", 80}, {"https", 443}};  // container: initializer list
```

Never this:

```cpp
Options options;            // default-constructed ...
options.width = 80;         // ... then filled in field by field
std::vector<int> sizes;     // or a run of mutators
sizes.push_back(4); sizes.push_back(8);
```

Why: assigning the same field twice compiles silently on every compiler, while naming a member twice in a
designated initializer is rejected or warned about (`designated_same_member_twice.cpp`,
`assign_same_member_twice.cpp`). The braced form also lets the object be `const`.

## Shape the type so the rule is easy to follow

- Required members first, with no default member initializer. Optional members after them, each with `{}` or a
  default. A caller then names the required ones and skips the rest (`designated_skip_member_with_default.cpp`).
- Designators must appear in declaration order. Reordering members is an API change.
- A type with a user-declared constructor is not an aggregate in C++20: `.member =` no longer compiles
  (`designated_on_type_with_constructor.cpp`). Do not add a constructor to a type you initialise by designators.

## When the type has no braced form, add one

For a class that only offers mutators (`add`, `set`, `insert`), give it a constructor that takes the whole contents
and **keeps the meaning of the mutator it replaces**: same order, and duplicates where the mutator kept them.
Declaring any constructor suppresses the implicit default constructor, so restore `T() = default;`.
See `references/patterns.md` (`container_type_with_initializer_list_constructor.cpp` is compiled by the tests).

## The exception

Contents you cannot know when you write the line - a loop over runtime data - use the range constructor or
`std::ranges::to`, not a braced list and not a mutator loop. Gate `std::ranges::to` on
`__cpp_lib_ranges_to_container` (`container_from_runtime_range.cpp`).

## Traps (measured; tables in `references/evidence.md`)

1. **Omitting a member that has no default** is a warning that only fires where `-Wextra` enables it.
   GCC 16 warns (`-Wmissing-field-initializers`); upstream Clang 19-23 warns
   (`-Wmissing-designated-field-initializers`); **Apple clang 21 says nothing**. With `-Werror` the first two
   reject. A green Mac (Xcode) build proves nothing. Check the target's flags before saying a mistake "fails"
   rather than "warns".
2. **Out-of-order designators**: GCC rejects, Clang only warns (`-Wreorder-init-list`).
3. **Designated initializers are C++20.** Under `-std=c++17` GCC 16 and Clang accept them silently; only
   `-pedantic-errors` rejects. Read the target's `cxx_std_*` rather than trusting that it compiled.
4. Mixing designated and positional initializers: GCC rejects, Clang warns (`-Wc99-designator`).

## Checklist

- [ ] Every object whose contents are known at the line is built by one braced expression.
- [ ] Required members first, optional members `{}` after them, designators in declaration order.
- [ ] Any constructor added keeps the old mutator's order and duplicates, and `T() = default;` is back.
- [ ] Checked with the project's real flags (`-Wextra`, `-Werror`, `-std=`) on GCC and upstream Clang.
