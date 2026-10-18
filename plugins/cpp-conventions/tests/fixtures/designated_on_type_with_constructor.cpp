struct Options {
    Options(int w) : width{w} {}
    int width;
    int height = 0;
};

const Options options{.width = 80};

int main() { return options.width == 80 ? 0 : 1; }
