int total_ms(int timeout_ms, int grace_s) { return timeout_ms + grace_s; }

int main() { return total_ms(1, 2) == 3 ? 0 : 1; }
