module;
#include <vector>
export module idioms;

template <class Sink>
void drain(Sink& out, int n) {
    out.write(n);
}

void log() {
    std::cout << "hello";
}

std::string render() {
    std::string out;
    out += "a";
    out += "b";
    out += "c";
    return out;
}

void quote(std::string& out, char c) {
    out += c == 1 ? std::string(1, c) : std::string{1, c};
}

int answer = 42;  // the answer
