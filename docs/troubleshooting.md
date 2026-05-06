# Troubleshooting

## Common Issues

### "No associated PR found. Skipping triage comment."

**Cause:** The bot couldn't link the failed workflow run to a PR.

This happens when:
- The workflow was triggered by a push to a branch without an open PR
- The workflow was triggered by `schedule`, `workflow_dispatch`, or other non-PR events
- The `workflow_run` event payload's `pull_requests` array is empty (common with cross-fork PRs) AND the search API fallback didn't find a matching PR

**Fix:** This is expected behavior — the bot only comments on PRs. If you want nightly failure tracking, see the [nightly-issue example](../examples/nightly-issue.yml).

### "OPENROUTER_API_KEY is not set"

**Cause:** The secret isn't available in the workflow context.

**Fix:**
1. Go to your repo Settings > Secrets and variables > Actions
2. Add a secret named `OPENROUTER_API_KEY` with your key from [openrouter.ai/keys](https://openrouter.ai/keys)
3. If you're using an organization secret, make sure the repo has access to it

### Comment appears but says "Log file was empty"

**Cause:** `gh run view --log-failed` returned empty output.

Possible reasons:
- The logs expired (GitHub retains logs for 90 days by default)
- The failure happened before any log output was produced (e.g., workflow syntax error)
- Permissions issue — the `github-token` doesn't have `actions: read` access

**Fix:** Check that your workflow has `actions: read` in permissions. If logs are expiring, consider running triage sooner.

### 403 error when posting comment

**Cause:** Insufficient permissions.

**Fix:** Ensure your workflow has these permissions:
```yaml
permissions:
  pull-requests: write
  actions: read
  contents: read
```

The default `github.token` for `workflow_run` events has limited scope. If you're in an organization with restricted token permissions, you may need to use a PAT or GitHub App token instead.

### OpenRouter returns an error

**Cause:** API key issue, rate limit, or model unavailable.

**Fix:**
1. Verify your API key is valid at [openrouter.ai/keys](https://openrouter.ai/keys)
2. Check your account balance — OpenRouter requires credits
3. Verify the model ID is correct (see [openrouter.ai/models](https://openrouter.ai/models))
4. Check OpenRouter status at [status.openrouter.ai](https://status.openrouter.ai)

The bot will print a warning but won't fail the workflow — a broken triage bot should never block your CI.

### Bot triggers but only on some failures

**Cause:** The `if` condition in the workflow filters events.

The default condition requires both:
1. `workflow_run.conclusion == 'failure'`
2. `workflow_run.event == 'pull_request'`

If your CI uses `pull_request_target` instead of `pull_request`, update the condition:
```yaml
if: >
  github.event.workflow_run.conclusion == 'failure' &&
  (github.event.workflow_run.event == 'pull_request' ||
   github.event.workflow_run.event == 'pull_request_target')
```

### Multiple triage comments on the same PR

**Cause:** Multiple jobs failed in the same workflow run, or the workflow was re-run.

The bot currently posts one comment per workflow_run event. Re-runs trigger new events. This is by design — each run may have different failure reasons.

**Workaround:** If this is noisy, you can add a step to check for existing bot comments before posting. This isn't built-in yet (see Roadmap).

## Debug Mode

To see more detail about what the bot is doing, check the workflow run logs for the triage job itself. The script prints to stdout/stderr with GitHub Actions annotations (`::error::`, `::warning::`).
