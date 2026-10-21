# The workflow template, line by line

`templates/bench-workflow.yml`:

- `on: workflow_dispatch` with inputs `script` and `runs`. No `push` or `pull_request` trigger: a benchmark on every push makes shared-runner noise a habit, and a gate on it would fail at random.
- `permissions: contents: read`: the job needs nothing else.
- **Inputs are data.** `${{ inputs.script }}` is copied into an environment variable and used as `"$SCRIPT"`; it is never written into the `run:` text, where a crafted value would become shell. The first step refuses a script that is not `bench/<name>.sh`, has `..` in it, has a character outside `[A-Za-z0-9_./-]`, or does not exist on the ref.
- The image is built from the repository (`docker build -t bench-image -f docker/Dockerfile docker`); change the line to the project's own. Running the script inside the same image the tests use means the compiler and library are the ones the claim is about.
- `docker run --rm -e RUNS -v "$PWD":/src:ro -w /src` mounts the tree read-only; the script writes to `/tmp`.
- The output goes to `bench.txt`, to the job summary and to an artifact.

## Dispatching a branch

`gh workflow run bench.yml --ref investigate/foo -f script=bench/drain_probe.sh` uses the workflow file and the script of that branch. The default-branch rule is only about the *workflow file*: the dispatch API refuses a workflow that the default branch does not have.

## Reading the result

The first line the script prints is the machine (`uname -m`, cores, compiler, runs, load). Copy it into the write-up with the run URL. The shape of a good record:

> GitHub ubuntu-24.04 runner, x86_64, 4 cores, GCC 16.2.0, 7 runs, load 1 to 2.5. [run 39480417966](https://github.com/wrocpp/reflect-moc/actions/runs/39480417966)
