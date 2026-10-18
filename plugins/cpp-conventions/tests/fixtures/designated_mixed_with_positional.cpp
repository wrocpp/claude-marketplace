struct Options {
    int width;
    int height = 0;
};

constexpr Options options{.width = 80, 24};

int main() { return options.width == 80 ? 0 : 1; }
