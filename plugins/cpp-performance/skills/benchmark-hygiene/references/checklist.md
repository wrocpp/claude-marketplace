# Benchmark checklist

Before a number is shown to anyone:

1. The gate passed for every design, and the wrong copy failed it (`tests/fixtures/gate`).
2. The designs differ in one thing. Name it in one sentence.
3. Runs alternated; the count and the order are in the output (`alternate.py` prints both).
4. The output has median, min and max, not a mean, and the load average before and after.
5. More than one size was run, or the one size is stated and said to be one point.
6. The order the benchmark visits things in is stated, and a second order was tried.
7. The same figure came out on a second quiet run, or the run says it did not.

## Writing the benchmark so alternate.py can read it

Print one line per measurement, nothing else on stdout (a progress note goes to stderr or starts with `#`):

```
e2e,qvariant,QHash,1000,drain,285.5
e2e,rqt,QHash,1000,drain,246.9
```

When the variant name is a field of the line, pass `--ignore-field 1` and run each design as its own command; the fields before and after it form the key. `alternate.py` reports a key only when every design reported it in every run, so a benchmark that crashes in one run does not give a median of fewer runs.

## Reading a spread

- A min-max range that overlaps the other design's range is not a difference.
- The median of 7 runs is robust to one bad run; the min-max shows it. If the max is several times the median, a run was disturbed: say so and repeat, do not drop it silently.
- A ratio of medians is `B/A` in the last column. The size of the cost matters as much: see the honest-claims skill.

## What the gate driver needs

- Seeded, so a failure repeats (the driver prints `seed 1 step N`).
- Checks the whole state after every step for small sizes, not only the last answer.
- Prints the first mismatch with the seed, the step and both values.
- Is the same source for every design: the implementation arrives through one header or one template parameter.
