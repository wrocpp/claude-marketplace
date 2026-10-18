struct Options {
    int width;
    int height = 0;
    bool wrap = false;
};

constexpr Options options{.width = 80, .height = 24, .wrap = true};

int main() { return options.width == 80 ? 0 : 1; }
