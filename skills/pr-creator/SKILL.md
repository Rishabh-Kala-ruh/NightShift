---
name: pr-creator
description: Commit, push branch, create PR via GitHub CLI, and update ticket with branch/PR info
---

# PR Creator

Handles the final steps after implementation: committing changes, pushing the branch, creating a pull request, and updating the ticket.

## Commit Format

```bash
cd <working_dir>

git add -A

# Commit message format:
# <TICKET-ID>: <ticket title>
#
# <short description of what was changed and why>
#
# Resolves: <TICKET-ID>
git commit -m "<TICKET-ID>: <ticket title>

<2-3 sentence summary of changes made>

Resolves: <TICKET-ID>"
```

## Push the Branch

```bash
git push origin "$BRANCH_NAME"
```

If push fails due to authentication, inform the user and stop -- do not attempt to configure credentials.

## Create a GitHub Pull Request

Use the GitHub CLI (`gh`) to create the PR:

```bash
gh pr create \
  --base dev \
  --head "$BRANCH_NAME" \
  --title "<TICKET-ID>: <ticket title>" \
  --body "$(cat <<'EOF'
## Summary
<What this PR does, in 2-3 sentences>

## Ticket
[<TICKET-ID>](<ticket-url>)

## Changes Made
<bullet list of files changed and what was done>

## Acceptance Criteria
<paste the acceptance criteria from the ticket>

## Test Results
<PASSED / FAILED WITH WARNINGS -- include error summary if warnings>
EOF
)"
```

Capture the PR URL from the output.

If `gh` is not installed or not authenticated, fall back to constructing the PR URL manually and tell the user to open it:

```
https://github.com/<org>/<repo>/compare/dev...<BRANCH_NAME>?expand=1
```

## Update Ticket

After PR creation:

- Transition the ticket to "Code Review" status
- Add a comment to the ticket:

```
Development complete. Branch and PR created automatically.

**Branch:** `<BRANCH_NAME>`
**PR:** <PR_URL>

Changes were committed and pushed. The ticket has been moved to Code Review.
```

## Final Output

After completing all steps, summarize what was done:

```
Done! Here's what happened for <TICKET-ID>:

**Files changed:**
- path/to/file1.ts
- path/to/file2.ts
```

## Error Handling

| Situation | Action |
|-----------|--------|
| Ticket not found | Stop, tell user, ask for correct ID |
| Branch already exists with commits | Ask user: reuse or abort |
| Git push fails (auth) | Stop, tell user to check GitHub credentials |
| `gh` not installed | Construct manual PR URL, tell user to open it |
| Tests fail | Commit with warning, note in PR description |
| Ticket transition not found | Skip transition, warn user, still add comment |
| Working directory not a git repo | Stop, inform user |

## Safety Rules

- Never modify `.env`, secrets, credentials, or security-related config
- Never force-push to `dev` or `main`
- Always branch from `dev`, not from the current HEAD (unless they are the same)
