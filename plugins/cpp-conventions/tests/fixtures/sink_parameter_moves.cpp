#include <string>
#include <utility>

class Label {
public:
    explicit Label(std::string text) : text_{std::move(text)} {}
    const std::string& text() const { return text_; }

private:
    std::string text_;
};

int main() { return Label{"x"}.text().size() == 1 ? 0 : 1; }
