# The ladder in commands

## Rung 2: a probe with no framework

Time each step alone and both together, for a list of N keys drained in random order. Precompute what the timed loop needs (the row each key has when it is removed) so the loop does only the steps.

```
probe,<pad>,<scan ns>,<remove ns>,<both ns>      # ns per key, mean over the drain
```

## Rung 3: shift the layout

```sh
for pad in 0 4 8 12 16 24 32 48 64 96 128 4096; do ./probe 100000 $pad; done
```

`pad` is a `malloc` kept alive before the list is allocated. A result that follows the pad is a layout effect (cache sets, alignment of the data); one that does not clears the data.

## Rung 4: the assembly

```sh
g++ -O2 -S file.cpp -o a.s                                  # one translation unit
objdump -d -C --no-show-raw-insn ./binary | sed 's/<[^>]*>//g' > binary.txt
sh disasm_function.sh ./binary hot_function                 # by unmangled substring
```

Keep addresses: a loop's fused `cmp` and `jne` are one unit for the front end, and the question is whether `start / 32 != (end - 1) / 32` or `end % 32 == 0`.

## Rung 5: the two flags

```sh
g++ -O2 -Wa,-mbranches-within-32B-boundaries file.cpp -o padded
g++ -O2 -falign-loops=64 file.cpp -o aligned
```

Both builds of both designs, alternating. On the run that solved it (x86_64, AMD EPYC, 100,000 hash entries): the typed build took 16.1 and the QVariant build 9.3 microseconds per removal; with the first flag both took 8.2; with the second both took 15.1. The flag is `-m` for the assembler (GNU as 2.34 and later); on aarch64 it does not exist, which is why the fixture prints SKIP there.

## Rung 6: remove the fragility

Replace the structure the loop walks, not the flags: a contiguous `std::vector` with `std::find` cost 7.6 microseconds a removal and 11.9 a replace in both builds, and scanned about 35 percent faster than `QList::indexOf` (13 against 20 microseconds for 100,000 keys, aarch64).

## Profile and syscalls

```sh
perf record -e cpu-clock -g ./binary        # when -e cycles says <not supported>
perf report --stdio | head -40
strace -c -f ./binary 2>&1 | tail -15
```

In the run above, essentially all samples were in the two model slots (46/46 typed, 60/30 QVariant, the expected 1:2 for a shrinking list against a fixed one), and `strace -c` showed start-up calls only.

## What to write down

The hypothesis, the one-line test of it, the result in both builds, and a sentence on what was not measured. If the mechanism is not known, say "moving the loop moves the cost" and stop there.
