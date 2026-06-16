# Z-Echo — Jira Integration via jira-cli

Instead of rolling out a custom Jira adapter, use the feature-rich **jira-cli** tool to sync issues to Jira.

Reference: https://github.com/ankitpokhrel/jira-cli

## Installation

Install jira-cli via Homebrew, package manager, or binary release:

```bash
# macOS
brew install jira-cli

# Or download from GitHub releases
# https://github.com/ankitpokhrel/jira-cli/releases
```

## Setup

1. Create a Jira API token in your Jira profile (Cloud: https://id.atlassian.com/manage-profile/security/api-tokens).
2. Export your token:
   ```bash
   export JIRA_API_TOKEN="your_api_token"
   ```
3. Run `jira init` to set up the configuration:
   ```bash
   jira init
   # Select "Cloud" or "Local"
   # Provide base URL and project key
   # This creates ~/.config/jira/config.yml
   ```

## Operations Mapping

### Create Issue
Instead of `JiraAdapter.upsert()` REST call, use:

```bash
jira issue create \
  -tBug \
  -s"<short_desc>" \
  -b"<body>" \
  --no-input \
  --raw
```

The `--raw` flag emits JSON output. Parse the returned JSON to extract the created issue `key` and the issue URL from `self`:

```bash
output=$(jira issue create -tBug -s"$summary" -b"$body" --no-input --raw)
key=$(jq -r '.key' <<<"$output")
link=$(jq -r '.self' <<<"$output")
```

Use `key` as the issue file name / identifier and store `jira_key` in frontmatter. Store `link` as `jira_link` for later reporting.

### Query Recently Changed Issues

Instead of `JiraAdapter.recently_changed()` JQL query, use:

```bash
jira issue list \
  --jql 'project=KEY AND status CHANGED TO (Done,Resolved,"Won'"'"'t Fix",Invalid) AFTER -5m' \
  --plain
```

Output format: one issue per line. Parse the output to extract key, status, and fixVersions.

**Plain format** example:
```
ISS-1  | Bug   | High    | John Doe    | To Do
ISS-2  | Task  | Medium  | Jane Smith  | Done
```

For more structured output, use `--json` or `--csv`:

```bash
jira issue list \
  --jql 'project=KEY AND status CHANGED TO (Done,Resolved,"Won'"'"'t Fix",Invalid) AFTER -5m' \
  --raw
```

## Integration Flow

1. **Triage pool → Jira**: Before writing the issue file, create the Jira bug with:
   ```bash
   output=$(jira issue create -tBug -s"<short_desc>" -b"<body>" --no-input --raw)
   key=$(jq -r '.key' <<<"$output")
   link=$(jq -r '.self' <<<"$output")
   ```
   Use `key` as the issue file name / identifier, set `jira_key`, and save `jira_link` in frontmatter.

2. **Jira → Pool (sync changes)**: At cron intervals, run:
   ```bash
   jira issue list --jql 'project=KEY AND status CHANGED TO (...) AFTER -5m' --plain
   ```
   Parse results and update issue file statuses and `fixed_in` versions.

## Environment Variables (Alternative to init)

If you prefer environment variables instead of `jira init`:

- **Cloud**: `JIRA_API_TOKEN` and `JIRA_HOST` (e.g., `https://yourinstance.atlassian.net`)
- **On-premise**: `JIRA_API_TOKEN`, `JIRA_HOST`, and optionally `JIRA_AUTH_TYPE=bearer`

## Error Handling

- **Authentication failure**: Ensure `JIRA_API_TOKEN` is valid and `jira init` completed.
- **Timeout**: Increase timeout with `--timeout` flag if needed.
- **Invalid JQL**: Test JQL syntax in your Jira UI before running commands.

## Shell Integration

Wrap jira-cli calls in your Python toolkit or cron scripts:

```python
import subprocess
import json

def create_jira_issue(summary: str, description: str) -> str:
    result = subprocess.run([
        "jira", "issue", "create",
        "-tBug", f"-s{summary}", f"-b{description}",
        "--no-input", "--raw"
    ], capture_output=True, text=True)
    if result.returncode == 0:
        return json.loads(result.stdout)["key"]
    raise RuntimeError(f"Jira creation failed: {result.stderr}")
```

## Further Reading

- Official docs: https://github.com/ankitpokhrel/jira-cli/wiki
- FAQs: https://github.com/ankitpokhrel/jira-cli/discussions/categories/faqs
- Advanced features: epic creation, linking, transitions, comments
