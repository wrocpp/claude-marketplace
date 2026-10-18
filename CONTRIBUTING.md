# Contributing

Thanks for helping. A plugin here should make Claude write better C++ for a reason you can show.

1. Read [docs/plugin-conventions.md](docs/plugin-conventions.md).
2. Open an issue for a new plugin before writing it; say which mistake it prevents and how you know.
3. Put the evidence in a fixture, not in prose: a `.cpp` that compiles or fails to compile.
4. Run the checks:

   ```bash
   python3 scripts/validate.py
   python3 scripts/sync.py --check
   claude plugin validate --strict .
   for p in plugins/*/tests/run.sh; do sh "$p"; done
   ```

5. Use conventional commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`), one logical change each.

Install a work-in-progress plugin into a throwaway Claude config so your own settings stay untouched:

```bash
export CLAUDE_CONFIG_DIR="$(mktemp -d)"
claude plugin marketplace add ./
claude plugin install cpp26-guard@wrocpp
```
