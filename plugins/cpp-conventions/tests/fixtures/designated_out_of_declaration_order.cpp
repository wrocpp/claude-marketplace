struct Options {
    int width;
    int height = 0;
};

constexpr Options options{.height = 24, .width = 80};

int main() { return options.width == 80 ? 0 : 1; }
