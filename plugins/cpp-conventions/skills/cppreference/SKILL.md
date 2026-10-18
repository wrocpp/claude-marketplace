---
name: cppreference
description: Use before asserting a C++ language or library rule that no build has already proved - validity, "since which standard", which header declares something, whether a construct is undefined. Confirms the rule against cppreference.com with a bundled script, caches pages locally so it works offline, and returns the page and section anchor to cite. Trigger phrases - is this valid C++, does the standard allow, since which C++ version, cppreference, why does gcc reject this, it compiles on clang, is this UB, which header declares, what does the standard say.
---

# Confirm a rule before you state it

A compiler accepting code is not the standard allowing it. When you are about to tell the user "this is
valid", "this is C++20", "this is undefined", or "header X declares it", look it up first, then cite what you found.

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/cppreference.py" lookup "designated initializer" --grep "same order"
python3 "${CLAUDE_SKILL_DIR}/scripts/cppreference.py" lookup cpp/container/span --grep "borrowed"
python3 "${CLAUDE_SKILL_DIR}/scripts/cppreference.py" lookup string_view --section Notes
python3 "${CLAUDE_SKILL_DIR}/scripts/cppreference.py" topics chrono
```

Output is the page, its section anchors, and short excerpts, each with a `cite:` URL such as
`https://en.cppreference.com/cpp/language/aggregate_initialization#Designated_initializer`.

## Procedure

1. Pick the page: an index word (`topics` lists them), a path (`cpp/<area>/<page>`), or a pasted URL.
2. `--grep` a distinctive phrase of the claim; or `--section <name>` to read one section (`sections:` lists them).
3. Read the excerpt. It is cut to a few hundred characters on purpose; if it does not settle the question,
   widen `--max-matches` or pick the neighbouring section.
4. State the rule **in your own words** and put the `cite:` URL next to it. Do not paste page text: cppreference
   is licensed CC BY-SA, and the explanation is yours to write.
5. If the page and the compiler disagree, say so and check which one the project targets (standard mode,
   compiler version): a rule "since C++20" may still compile under C++17 as an extension.

Exit status: `0` matches, `1` page loaded but nothing matched (try another phrase or section), `2` page unavailable.
On `2`, say the rule is unconfirmed; do not assert it.

## Cache and network

- Pages are cached under `$WROCPP_CACHE_DIR` (default `~/.cache/wrocpp/cppreference`).
- A page that is not cached is fetched once (one request per page, with a descriptive User-Agent). `--offline` or
  `WROCPP_OFFLINE=1` forbids the network; then only cached pages answer. `--refresh` fetches again.
- Seed the cache while online for the pages a project uses, and the skill keeps working offline.

## What it cannot do

It searches one page at a time and does not know about every cppreference page: use `topics` for the index, or
give the path. It reports the site's wording, which is a summary of the standard and sometimes lags it; for a
normative question cite the standard clause as well, and for compiler behaviour prefer a fixture
(see `no-needless-copies` and `designated-init` for the pattern).
