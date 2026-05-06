"""Summarize a failed GitHub Actions run into a concise Markdown triage block.

Uses OpenRouter (OpenAI-compatible gateway) to call an LLM.
Designed to run inside a GitHub Actions composite action.

Configuration via environment variables:
    OPENROUTER_API_KEY  (required)  -- OpenRouter API key
    GITHUB_REPOSITORY   (auto)      -- owner/repo, injected by Actions
    INPUT_MODEL         (optional)  -- model identifier (default: anthropic/claude-haiku-4.5)
    INPUT_MAX_TOKENS    (optional)  -- response token limit (default: 800)
    INPUT_MAX_LOG_LINES (optional)  -- max log lines to send (default: 200)
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import time
from typing import NoReturn

from openai import OpenAI

DEFAULTS = {
    "model": "anthropic/claude-haiku-4.5",
    "max_tokens": 800,
    "max_log_lines": 200,
}


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def die(msg: str, code: int = 1) -> NoReturn:
    print(f"::error::{msg}", file=sys.stderr)
    sys.exit(code)


def resolve_pr_number() -> str | None:
    """Extract the PR number from the workflow_run event payload."""
    event_path = env("GITHUB_EVENT_PATH")
    if not event_path or not pathlib.Path(event_path).exists():
        return None

    payload = json.loads(pathlib.Path(event_path).read_text(encoding="utf-8"))
    wr = payload.get("workflow_run", {})

    prs = wr.get("pull_requests") or []
    if prs:
        return str(prs[0]["number"])

    head_sha = wr.get("head_sha")
    repo = env("GITHUB_REPOSITORY")
    if not head_sha or not repo:
        return None

    for attempt in range(3):
        result = subprocess.run(
            ["gh", "api", f"search/issues?q=repo:{repo}+is:pr+sha:{head_sha}"],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            return None
        items = json.loads(result.stdout).get("items", [])
        if items:
            return str(items[0]["number"])
        # GitHub search index may lag; wait before retrying
        if attempt < 2:
            time.sleep(2 ** attempt)

    return None


def fetch_failed_log(run_id: str, repo: str, max_lines: int) -> str:
    """Download the failed log via gh CLI and trim to max_lines."""
    result = subprocess.run(
        ["gh", "run", "view", run_id, "-R", repo, "--log-failed"],
        capture_output=True, text=True,
    )
    log = result.stdout.strip()
    if not log:
        return ""
    lines = log.splitlines()
    return "\n".join(lines[-max_lines:])


def generate_triage(log: str, repo: str, model: str, max_tokens: int) -> str:
    """Call the LLM via OpenRouter and return the triage markdown."""
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=env("OPENROUTER_API_KEY"),
        default_headers={
            "HTTP-Referer": f"https://github.com/{repo}",
            "X-Title": "CI Triage Bot",
        },
    )

    resp = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=[
            {
                "role": "system",
                "content": (
                    f"You are a CI triage assistant for the GitHub repository {repo}. "
                    "Given the tail of a failed GitHub Actions log, produce a terse, "
                    "actionable Markdown report for the PR author. Focus on root cause "
                    "over symptoms. Do not repeat the log verbatim. Do not invent file "
                    "paths or APIs that are not visible in the log."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Analyze the failed CI log below and output markdown EXACTLY in this structure:\n\n"
                    "**Failed job:** <job name, or 'unknown' if not identifiable>\n"
                    "**Likely cause:** <one concise sentence>\n"
                    "**Hypotheses (max 3):**\n"
                    "1. <most likely>\n"
                    "2. ...\n"
                    "**Suggested fix:** <concrete next step -- file path, command, or one-line code change>\n"
                    "**Confidence:** low | medium | high\n\n"
                    "--- LOG TAIL ---\n"
                    f"{log}"
                ),
            },
        ],
    )

    return (resp.choices[0].message.content or "").strip()


def main() -> int:
    if "--help" in sys.argv:
        print(__doc__)
        return 0

    api_key = env("OPENROUTER_API_KEY")
    if not api_key:
        die("OPENROUTER_API_KEY is not set.")

    repo = env("GITHUB_REPOSITORY", "unknown/unknown")
    model = env("INPUT_MODEL", DEFAULTS["model"])
    max_tokens = int(env("INPUT_MAX_TOKENS", str(DEFAULTS["max_tokens"])))
    max_log_lines = int(env("INPUT_MAX_LOG_LINES", str(DEFAULTS["max_log_lines"])))

    event_path = env("GITHUB_EVENT_PATH")
    if not event_path:
        die("GITHUB_EVENT_PATH is not set. This script must run inside GitHub Actions.")

    payload = json.loads(pathlib.Path(event_path).read_text(encoding="utf-8"))
    run_id = str(payload.get("workflow_run", {}).get("id", ""))
    run_url = payload.get("workflow_run", {}).get("html_url", "")

    if not run_id:
        die("Could not find workflow_run.id in event payload.")

    pr_number = resolve_pr_number()

    log = fetch_failed_log(run_id, repo, max_log_lines)
    if not log:
        triage = (
            "**Failed job:** unknown\n"
            "**Likely cause:** Log file was empty or could not be downloaded.\n"
            "**Suggested fix:** Inspect the run manually.\n"
            "**Confidence:** low"
        )
    else:
        triage = generate_triage(log, repo, model, max_tokens)

    header = f"## 🤖 CI Triage (auto)\nRun: {run_url}\n\n"
    body = header + triage

    if pr_number:
        result = subprocess.run(
            ["gh", "pr", "comment", pr_number, "-R", repo, "--body", body],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print(f"::warning::Failed to post PR comment: {result.stderr.strip()}")
            print(triage)
            return 0
        print(f"Triage comment posted on PR #{pr_number}")
    else:
        workflow_name = payload.get("workflow_run", {}).get("name", "CI")
        issue_title = f"CI Triage: {workflow_name} failed"
        subprocess.run(
            ["gh", "label", "create", "ci-triage-auto",
             "-R", repo, "--color", "D4C5F9",
             "--description", "Auto-created by CI Triage Bot", "--force"],
            capture_output=True, text=True,
        )

        existing = subprocess.run(
            ["gh", "issue", "list", "-R", repo,
             "--label", "ci-triage-auto", "--state", "open",
             "--search", f"in:title {workflow_name}",
             "--json", "number", "--limit", "1"],
            capture_output=True, text=True,
        )
        existing_number = None
        if existing.returncode == 0:
            issues = json.loads(existing.stdout or "[]")
            if issues:
                existing_number = str(issues[0]["number"])

        if existing_number:
            result = subprocess.run(
                ["gh", "issue", "comment", existing_number,
                 "-R", repo, "--body", body],
                capture_output=True, text=True,
            )
            if result.returncode != 0:
                print(f"::warning::Failed to comment on issue #{existing_number}: {result.stderr.strip()}")
                print(triage)
                return 0
            print(f"Triage comment added to existing issue #{existing_number}")
        else:
            result = subprocess.run(
                ["gh", "issue", "create", "-R", repo,
                 "--title", issue_title, "--body", body,
                 "--label", "ci-triage-auto"],
                capture_output=True, text=True,
            )
            if result.returncode != 0:
                print(f"::warning::Failed to create issue: {result.stderr.strip()}")
                print(triage)
                return 0
            print(f"Triage issue created: {result.stdout.strip()}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
