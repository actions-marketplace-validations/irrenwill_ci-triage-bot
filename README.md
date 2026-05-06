# CI Triage Bot

**AI-powered CI failure analysis that posts actionable triage comments on your PRs.**

<!-- TODO: Record a demo GIF and place it at docs/demo.gif -->
<!-- ![demo](docs/demo.gif) -->

## Why

CI fails. You click into the run, scroll through hundreds of log lines, squint at the error, and figure out what went wrong. Every time.

CI Triage Bot does the squinting for you. When a workflow fails on a PR, it reads the failed job's logs, sends them to an LLM, and posts a structured triage comment — root cause, hypotheses, and a suggested fix — directly on the PR. Median cost per triage: ~$0.002.

## Quick Start

**1. Get an [OpenRouter API key](https://openrouter.ai/keys)** and add it as a repository secret named `OPENROUTER_API_KEY`.

**2. Create `.github/workflows/ci-triage.yml`** in your repo:

```yaml
name: CI Triage
on:
  workflow_run:
    workflows: ["CI"]  # <-- replace with YOUR workflow name
    types: [completed]

permissions:
  pull-requests: write
  actions: read
  contents: read

jobs:
  triage:
    if: >
      github.event.workflow_run.conclusion == 'failure' &&
      github.event.workflow_run.event == 'pull_request'
    runs-on: ubuntu-latest
    steps:
      - uses: irrenwill/ci-triage-bot@v1
        with:
          openrouter-key: ${{ secrets.OPENROUTER_API_KEY }}
```

**3. Push, break CI, and watch the comment appear.**

## How It Works

```
PR push ──> CI workflow runs ──> fails
                                   │
                        workflow_run event fires
                                   │
                          CI Triage Bot runs:
                            1. Find the PR number
                            2. Download failed job logs (gh CLI)
                            3. Trim to last N lines
                            4. Send to LLM via OpenRouter
                            5. Post structured comment on PR
```

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `openrouter-key` | **Yes** | — | Your [OpenRouter API key](https://openrouter.ai/keys) |
| `model` | No | `anthropic/claude-haiku-4.5` | Any model available on OpenRouter |
| `max-log-lines` | No | `200` | Max log lines sent to the model |
| `max-tokens` | No | `800` | Max tokens in the model response |
| `github-token` | No | `${{ github.token }}` | Token for posting comments and reading logs |

## Output Format

The bot posts a comment with this structure:

> **Failed job:** test-unit
> **Likely cause:** Missing dependency `foo` in requirements.txt
> **Hypotheses (max 3):**
> 1. `foo` was removed from requirements.txt in this PR
> 2. Transitive dependency conflict after upgrading `bar`
> **Suggested fix:** Add `foo>=2.0` to requirements.txt
> **Confidence:** high

## FAQ

**How much does it cost?**
Claude Haiku 4.5 via OpenRouter costs ~$0.001-0.003 per triage. A repo with 10 CI failures per day would cost roughly $0.50-1.00/month. You can check usage at [openrouter.ai/usage](https://openrouter.ai/usage).

**Can I use a different model?**
Yes. Set the `model` input to any model ID available on OpenRouter (e.g., `google/gemini-2.5-flash`, `openai/gpt-4.1-mini`). See [openrouter.ai/models](https://openrouter.ai/models) for the full list.

**Does my code get sent to OpenRouter?**
Only the **failed log output** (last 200 lines by default) is sent. Source code is not included unless it appears in the log. OpenRouter's privacy policy applies to data in transit. If this is a concern, reduce `max-log-lines` or use a model with stricter data policies.

**Why OpenRouter instead of direct Anthropic/OpenAI?**
OpenRouter gives you model flexibility with a single API key. You can switch between Claude, GPT, Gemini, or open-source models without changing your workflow. If you want direct Anthropic, you can self-host a compatible proxy — the script uses the standard OpenAI SDK client.

**Does it work with `pull_request_target`?**
Yes. The `workflow_run` trigger fires for both `pull_request` and `pull_request_target` events. The bot resolves the PR number from either.

**What if no PR is associated with the failed run?**
The bot exits gracefully with a success status. No comment is posted, no error is raised.

## Roadmap

- [ ] Configurable comment template (custom prompt / output format)
- [ ] Slack / Discord notification option alongside PR comments
- [ ] Multi-job triage (analyze each failed job separately)
- [ ] Failure pattern memory (detect recurring failures across runs)
- [ ] Direct Anthropic API support (bypass OpenRouter)

## Examples

See the [`examples/`](examples/) directory for complete, copy-pastable workflow files:

- [`basic-usage.yml`](examples/basic-usage.yml) — Minimal setup
- [`custom-model.yml`](examples/custom-model.yml) — Override model and token limit
- [`nightly-issue.yml`](examples/nightly-issue.yml) — Combine triage with auto-issue creation for nightly builds

## License

[MIT](LICENSE)
