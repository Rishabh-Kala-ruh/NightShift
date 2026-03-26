---
name: pathfinder-reader
description: Parse Pathfinder analysis comments (RCA for bugs, TRD for features) to extract repos, file hints, and code changes
---

# Pathfinder Reader

Parses structured comments left by the Pathfinder automation on Linear tickets.

## Comment Types

| Ticket Type | Comment Contains |
|-------------|-----------------|
| Bug | RCA: symptom, root cause trace, fix approach, code changes table |
| Feature | TRD: requirements, technical design, code changes table, implementation order |
| Task | Task breakdown: what to do, affected files |

## Extracted Data

- **Classification:** BUG / FEATURE / TASK
- **Complexity:** S / M / L / XL
- **Repos Affected:** ordered list (first = primary)
- **Code Changes Table:** file, function, change type (MODIFY/ADD/NEW FILE/VERIFY), description
- **File Hints:** paths and symbols from the analysis trace
- **Implementation Order:** ordered repo list for multi-repo changes

## Repo Detection Formats

Handles multiple Pathfinder comment formats:
1. `**Repos Affected:** agent-platform-v2 (primary), ai-gateway`
2. `#### Repo 1: \`agent-platform-v2\` (Primary Changes)`
3. Affected Files Summary table rows
