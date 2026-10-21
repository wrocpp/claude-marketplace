---
name: measure-on-ci
description: Use when a measurement needs a second machine, when a result came from a busy laptop, when a benchmark must run on x86_64 and the developer has only an ARM Mac, or when setting up a manual benchmark workflow in GitHub Actions. A workflow_dispatch workflow takes the script name as an input and runs it in the repository's own image; it must exist on the default branch to be dispatched. Trigger phrases - "run the benchmark on CI", "x86_64 numbers", "workflow_dispatch", "gh workflow run", "second machine", "benchmark workflow", "measure on a runner".
---

# Measure on CI

A laptop that is in use gives a noisy first figure. A manual workflow on a CI runner gives a second machine, often a different architecture, and on GitHub's `ubuntu-24.04` runner a small spread (under 2 percent in most cells in the run behind this plugin). It is a record to read beside the local numbers, never a gate: shared runners are noisy.

## Set it up once

Copy the template and the harness into the repository:

```sh
mkdir -p bench .github/workflows
cp "${CLAUDE_PLUGIN_ROOT}/templates/bench-workflow.yml" .github/workflows/bench.yml
cp "${CLAUDE_PLUGIN_ROOT}/templates/run-bench.sh" bench/run-bench.sh
cp "${CLAUDE_PLUGIN_ROOT}/scripts/alternate.py" bench/alternate.py
```

Then point the image step at the project's own Dockerfile. The workflow takes the **script name as an input**, so the same workflow runs the main benchmark and every probe (`bench/drain_probe.sh`, ...) without a new file for each. It checks the name (`bench/<name>.sh`, no `..`), passes every input through `env` and never into the shell text, runs the script in the repository's image with the tree mounted read-only, and uploads the output.

## Dispatch it

```sh
gh workflow run bench.yml -f script=bench/run-bench.sh -f runs=7
gh run list --workflow bench.yml --limit 1
gh run view <id> --log | less        # or download the artifact "bench"
```

- **The workflow file must exist on the default branch before it can be dispatched.** Merge it first, even if the benchmark script is still on a branch.
- `--ref my-branch` then runs *that branch's version* of the workflow and the script. This is how an investigation branch gets measured without merging: each probe is a commit and a dispatch, and each run is a link.
- Read the load average the script prints at the start and the end; a runner with a load of 1 to 2.5 gave readable numbers, one with more did not.

## Use the second machine for what it is good for

- A different architecture checks a claim that came from the laptop: a change measured slower for one operation on the Mac and faster on x86_64 in the run behind this plugin.
- A probe on the runner can show a placement or layout effect that the laptop does not have, but the runner is a VM: hardware counters may be `<not supported>`, so say what was not read ([slowdown-ladder](../slowdown-ladder/SKILL.md)).
- Link the run in the write-up ([honest-claims](../honest-claims/SKILL.md)) and say it is one run.

Details, the permissions the workflow needs and why it is manual only: [references/dispatch.md](references/dispatch.md).
