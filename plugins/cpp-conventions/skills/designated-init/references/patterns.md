# Patterns

## Aggregate with required and optional members

```cpp
struct Request {
    std::string url;                 // required: no default, first
    std::string method = "GET";      // optional
    std::chrono::milliseconds timeout{};
};

const Request request{.url = "https://example.org/", .timeout = std::chrono::seconds{5}};
```

`method` is skipped (it has a default), and `timeout` follows `url` in declaration order.

## Class that only had mutators

Before:

```cpp
Headers headers;
headers.add("accept", "text/html");
headers.add("accept", "application/json");   // duplicates are kept
```

After - add the constructor, reusing the mutator so order and duplicates stay as they were, and restore the
defaulted default constructor:

```cpp
class Headers {
public:
    Headers() = default;
    Headers(std::initializer_list<std::pair<std::string, std::string>> fields) {
        for (const auto& [name, value] : fields) add(name, value);
    }
    void add(std::string name, std::string value);
};

const Headers headers{{"accept", "text/html"}, {"accept", "application/json"}};
```

## Runtime data

```cpp
auto doubled = input | std::views::transform(twice) | std::ranges::to<std::vector>();   // C++23
std::vector<int> doubled(input.begin(), input.end());                                  // range constructor
```

Do not write `std::vector<int> out; for (...) out.push_back(...)` for a plain transformation.

## Passing owned values into a braced form

Sink members take their argument by value and move it (see the `no-needless-copies` skill):

```cpp
Request make(std::string url) { return {.url = std::move(url)}; }
```
