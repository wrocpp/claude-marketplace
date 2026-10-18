struct Options {
    int width;
    int height;
};

constexpr Options options{.width = 80};

int main() { return options.width == 80 ? 0 : 1; }
