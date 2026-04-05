# Contributing to paperflow

paperflow is a personal research tool that I've open-sourced in case it's useful to others. Contributions are welcome with the caveat that I maintain this on a best-effort basis.

## What I'll review

- Bug fixes with a clear reproduction case
- New research direction configs (additions to `config/` YAML files)
- Improvements to the fetch / score / ingest pipeline
- Documentation fixes and clarifications

## What I won't accept

- Changes that couple the tool to a specific cloud provider or require accounts
- Features that require a persistent server or user accounts
- UI rewrites of the Flask dashboard
- Breaking changes to the YAML data format

## How to contribute

1. **Open an issue first** to describe what you want to build or fix. This avoids wasted effort on both sides.
2. Fork the repo, implement your change, and add a test if applicable.
3. Open a pull request that references the issue.

The project has a test suite — run `make test` before submitting. PRs that break existing tests won't be merged.
