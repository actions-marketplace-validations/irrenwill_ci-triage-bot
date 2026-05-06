# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

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
