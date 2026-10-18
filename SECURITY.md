# Security

These plugins run inside other people's repositories, so their threat model matters.

## What they do and do not do

- Hooks are advisory: they add a note for Claude and exit 0. They never block an edit unless the
  project turns that on in `.claude/<plugin>.json`.
- Anything read from the project being edited is untrusted: config files, source text, file names,
  allowance and triage files, fuzzer findings, and text fetched from the web. Hooks and scripts
  validate it before it reaches a command line or Claude's context, and quote what they show.
  See [docs/plugin-conventions.md](docs/plugin-conventions.md).
- Scripts that run build or test commands take them from the command line or fixed forms, never as a
  shell string from a project file. Values that become arguments cannot start with `-`.

## What you should still do

- Read `.claude/*.json` and any script a project asks you to run before using these plugins in a
  repository you do not trust, exactly as you would read its build files.
- Treat a configured build or test command as running with your privileges.

## Reporting a vulnerability

Use GitHub's private vulnerability reporting on this repository (Security tab, "Report a
vulnerability"). Please do not open a public issue for a security problem. Include the plugin, the
version, and the smallest input that shows the problem; a canary file that gets deleted or a string
that reaches Claude's context is ideal.
