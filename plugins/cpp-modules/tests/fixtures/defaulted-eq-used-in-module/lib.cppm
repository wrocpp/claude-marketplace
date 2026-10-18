export module lib;

export namespace lib {

struct point {
  int x{};
  int y{};
  friend constexpr bool operator==(point const&, point const&) = default;
};

}  // namespace lib

static_assert(lib::point{1, 2} == lib::point{1, 2});
