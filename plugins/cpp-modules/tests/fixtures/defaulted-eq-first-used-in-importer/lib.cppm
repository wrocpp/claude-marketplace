export module lib;

export namespace lib {

struct point {
  int x{};
  int y{};
  friend constexpr bool operator==(point const&, point const&) = default;
};

}  // namespace lib
