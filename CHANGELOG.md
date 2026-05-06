# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [1.0.1] - 2026-05-06

### Fixed
- Workflow examples no longer filter on `workflow_run.event == 'pull_request'`,
  which caused the action to silently skip when CI was triggered by `push`
  events. The script itself already handled non-PR runs gracefully via
  SHA-based PR lookup; only the example YAML needed updating.
- Updated README Quick Start, `examples/basic-usage.yml`,
  `examples/custom-model.yml`, and `examples/nightly-issue.yml` with an
  explicit event list (`pull_request`, `push`, `workflow_dispatch`).
- Added `::notice::` annotation when no PR is found, so users see a clear
  message in the workflow summary instead of silent exit.

### Notes
- Users on `@v1` automatically receive this fix.
- Users pinned to `@v1.0.0` are not affected (their existing workflows
  continue to work; this fix expands coverage to push-triggered CI).

## [1.0.0] - 2026-05-06

### Added
- Initial public release
- AI-powered CI failure analysis via OpenRouter (OpenAI SDK compatible)
- Configurable model, log lines, and token limit
- Structured PR comment: failed job, root cause, hypotheses, suggested fix, confidence
- Graceful handling of missing PRs, empty logs, and non-PR workflow runs
- Three example workflows: basic, custom model, nightly issue creation

### Known Limitations
- Each failed run posts a new comment; re-runs accumulate multiple comments (#1)
- Multi-job failures are analyzed as a single consolidated log, not per-job (#2)
- Forked PRs may not receive comments due to GitHub token permission model (#3)
