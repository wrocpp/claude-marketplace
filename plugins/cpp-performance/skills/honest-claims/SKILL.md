---
name: honest-claims
description: Use before writing a performance claim anywhere - a README, a commit message, a pull request, a blog post, a table - and when correcting one. A measurement is not a claim until a quiet re-run agrees; give the size of the cost and not only the ratio; report the cost on the other side too (bytes, binary size, compile time); correct a published claim by replacing it, not by adding a new one beside it; label what was measured before a change and after. Trigger phrases - "faster than", "within 10 percent", "the numbers say", "write up the benchmark", "publish the results", "correct the post", "update the measurements", "speedup", "overhead".
---

# Honest claims

The measurement is the easy part. These rules are about the sentence written afterwards.

1. **A measurement is not a claim until a quiet re-run agrees.** "Faster or equal in all ten rows" was published from one run on a busy machine. A quiet re-run found typed signals 4 to 15 percent slower for one operation on the Mac (an emit with no receiver costs about 10 ns) and 3 to 18 percent faster on x86_64, while the busy-Mac run had said the opposite. Repeat on a quiet machine, ideally a second one ([measure-on-ci](../measure-on-ci/SKILL.md)), before the sentence is written.
2. **Give the size of the cost, not only the ratio.** A change cost 70 to 320 ns in either design: "within 10 percent" of 200 ns is 20 ns. Write both: `10 percent, about 20 ns of a 200 ns change`. A big ratio of a small number, and a small ratio of a big one, mean different things.
3. **Report the cost on the other side too.** The faster design was 112 bytes per container against 24, its binary 27 percent larger on x86_64 (189,760 against 149,088 bytes), and one translation unit took 3.2 s longer to compile (9.83 against 6.61 s), within 4 percent of the alternative once moc and its output were counted. A claim with only the benefit is an advertisement.
4. **Correct by replacing.** When a number is wrong, change the sentence, the table and the post where it stands, and say in the commit what changed and why. Do not add a new figure beside the old one: a reader finds the first and stops. The old claim in the run behind this plugin was removed, not left beside the new one.
5. **Label what was measured before a change and after.** A table that mixes figures from before and after a fix reads as one result. Say which rows were measured with which version ("the tables above used the `QList` key list; read the removal rows in that light"), the machine, the compiler, the runs and the load.
6. **Two independently written implementations are not a controlled comparison.** A spec was regenerated twice by two fresh agents, once with `QVariant` keys and once with typed signals, and the same benchmark source ran against both. Per entry the two models do the same work and typed was 16 to 42 percent faster, but the batch and reset rows also differ in model code, so a gap there cannot be put down to the signal. `resetWith` read 23 to 29 percent slower on a busy Mac and 8 percent slower on x86_64; the cause was never found. Say which rows are comparable, label the others "different code", and do not draw the conclusion the first design question wanted ([benchmark-hygiene](../benchmark-hygiene/SKILL.md) rule 2).
7. **Say what was not measured.** One compiler, one machine for the main run, no view attached, no hardware counters, the mechanism not identified. Put it in a section of its own, not a footnote.

## Before you publish

- [ ] The gate passed and the wrong copy failed ([benchmark-hygiene](../benchmark-hygiene/SKILL.md)).
- [ ] A quiet re-run agrees, and the load average is in the write-up.
- [ ] Ratio and absolute cost both stated; the other side's cost stated.
- [ ] Numbers carry the machine, compiler, runs and a run link; old figures are replaced.
- [ ] Rows that compare two separately written implementations are labelled, not read as one design question.
- [ ] "Not measured" is written down.

The numbers this plugin was built from, with the CI run behind each, are in [references/evidence.md](references/evidence.md). They were measured on those runs only.
