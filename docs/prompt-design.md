# Prompt Design

This document explains the prompt strategy used by CI Triage Bot.

## Goal

Turn a wall of CI log text into a 5-line actionable summary. The reader is the PR author — someone who knows the codebase but doesn't want to scroll through raw logs.

## Prompt Structure

The LLM receives two messages:

### System message

Sets the role ("CI triage assistant for repo X") and constraints:
- Focus on root cause, not symptoms
- Don't parrot the log verbatim
- Don't hallucinate file paths or APIs not visible in the log

The repo name is injected so the model has context about what project it's analyzing.

### User message

Asks for a structured output with these fields:

| Field | Purpose |
|-------|---------|
| **Failed job** | Identifies which job in the workflow failed (helps in multi-job workflows) |
| **Likely cause** | One-sentence root cause — the most important line |
| **Hypotheses (max 3)** | Ranked alternatives when the cause isn't certain |
| **Suggested fix** | A concrete next step: file to edit, command to run, or config to change |
| **Confidence** | Self-assessed certainty — helps the reader decide whether to trust or investigate further |

The actual log content follows after a `--- LOG TAIL ---` separator.

## Why Structured Output

Free-form analysis tends to ramble. The fixed structure:
1. Makes the comment scannable in 5 seconds
2. Keeps the model focused on actionable information
3. Makes it easy to build automation on top (parse confidence, filter by job name, etc.)

## Why "Hypotheses" Instead of Just "Root Cause"

CI failures are often ambiguous. A test might fail because of:
- A real bug in the PR
- A flaky test
- An environment change on the runner

Forcing ranked hypotheses acknowledges this ambiguity and gives the reader multiple threads to pull.

## Log Trimming

Only the last N lines (default: 200) are sent. This is intentional:
- Most CI failures have the relevant error at the end of the log
- Sending the full log wastes tokens on setup steps, dependency installation, etc.
- 200 lines is enough for most error traces while staying well within context limits

If 200 lines isn't enough for your logs (e.g., verbose test output), increase `max-log-lines`.

## Known Limitations

- **Build logs with interleaved parallel output** can confuse the model — it may attribute errors to the wrong job
- **Truncated stack traces** (when the error starts before the 200-line window) lead to low-confidence guesses
- **Infrastructure failures** (runner out of disk, network timeout) are identified correctly but the "suggested fix" is less useful since there's nothing to change in code
- **Secrets in logs** — if your CI accidentally prints secrets, they will be sent to OpenRouter. This is a CI hygiene issue, not a bot issue, but be aware

## Customizing the Prompt

The prompt is in `src/ci_triage.py` in the `generate_triage()` function. To customize:

1. Fork the repo
2. Edit the `messages` list in `generate_triage()`
3. Point your workflow at your fork: `uses: your-fork/ci-triage-bot@main`

Common customizations:
- Add project-specific context to the system message ("This is a Python/Django project using pytest")
- Change the output structure (add a "Related docs" field, remove hypotheses)
- Add language constraints ("Respond in Japanese")
