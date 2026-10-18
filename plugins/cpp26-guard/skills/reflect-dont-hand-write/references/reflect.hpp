#pragma once
#include <array>
#include <cstddef>
#include <meta>
#include <optional>
#include <string_view>
#include <type_traits>

namespace refl {

template <class E>
    requires std::is_enum_v<E>
inline constexpr auto enumerators = std::define_static_array(std::meta::enumerators_of(^^E));

template <class E>
inline constexpr std::size_t enum_count = enumerators<E>.size();

template <class E>
consteval auto make_values() {
    std::array<E, enum_count<E>> values{};
    std::size_t next = 0;
    template for (constexpr auto e : enumerators<E>) {
        values[next++] = [:e:];
    }
    return values;
}

template <class E>
inline constexpr auto enum_values = make_values<E>();

template <class E>
consteval bool unique_values() {
    for (std::size_t i = 0; i < enum_count<E>; ++i) {
        for (std::size_t j = i + 1; j < enum_count<E>; ++j) {
            if (enum_values<E>[i] == enum_values<E>[j]) {
                return false;
            }
        }
    }
    return true;
}

template <class E>
constexpr std::string_view enum_name(E const value) noexcept {
    template for (constexpr auto e : enumerators<E>) {
        if (value == [:e:]) {
            return std::meta::identifier_of(e);
        }
    }
    return {};
}

template <class E>
constexpr std::optional<E> enum_from_name(std::string_view const word) noexcept {
    template for (constexpr auto e : enumerators<E>) {
        if (word == std::meta::identifier_of(e)) {
            return [:e:];
        }
    }
    return std::nullopt;
}

template <class A>
consteval bool has_annotation(std::meta::info const member) {
    return !std::meta::annotations_of_with_type(member, ^^A).empty();
}

template <class A>
consteval A annotation_of(std::meta::info const member) {
    return std::meta::extract<A>(std::meta::annotations_of_with_type(member, ^^A).front());
}

template <class T>
inline constexpr auto members = std::define_static_array(std::meta::nonstatic_data_members_of(^^T, std::meta::access_context::unprivileged()));

template <class T, class Visit>
    requires std::is_aggregate_v<T>
constexpr void for_each_member(T const& object, Visit&& visit) {
    template for (constexpr auto m : members<T>) {
        visit(std::meta::identifier_of(m), object.[:m:]);
    }
}

struct flag {
    char text[24];
    constexpr std::string_view view() const noexcept { return text; }
};

consteval flag make_flag(std::string_view const spelling) {
    flag result{};
    for (std::size_t i = 0; i < spelling.size() && i + 1 < sizeof result.text; ++i) {
        result.text[i] = spelling[i];
    }
    return result;
}

template <class Options>
constexpr bool set_flag(Options& options, std::string_view const word) {
    template for (constexpr auto m : members<Options>) {
        if constexpr (has_annotation<flag>(m)) {
            if (word == annotation_of<flag>(m).view()) {
                options.[:m:] = true;
                return true;
            }
        }
    }
    return false;
}

}  // namespace refl
