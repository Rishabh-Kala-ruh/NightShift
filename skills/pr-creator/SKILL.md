---
name: pr-creator
description: Push branch to origin and create a PR to dev using GitHub CLI
---

# PR Creator

Handles the final step: pushing the branch and creating a pull request.

## Flow

1. Check if any commits exist (git diff HEAD~1 --stat)
2. Check for CLAUDE_UNABLE.md (skip if present)
3. Push branch to origin
4. Detect GitHub owner/repo from git remote URL
5. Create PR via `gh pr create --base dev`
6. Return PR URL

## PR Format

- **Title:** `fix(TICKET-ID): ticket title`
- **Base branch:** always `dev` (configured via TARGET_BRANCH)
- **Body:** ticket title, Linear link, description

## Linear Update

After PR creation:
- Move ticket to "Code Review" state
- Comment on ticket with: PR links, commit summary, files changed, Pathfinder context, review checklist
