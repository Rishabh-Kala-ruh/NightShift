---
name: ticket-scanner
description: Fetch eligible tickets from Linear API, filter by state and assignee, sort by priority
---

# Ticket Scanner

Connects to Linear GraphQL API and fetches tickets that are ready for autonomous development.

## Filter Criteria

- **State:** "Ready for Development" (fallback: "unstarted" / "started")
- **Assignee:** Current authenticated user
- **Excludes:** Already processed tickets, tickets with "claude-processing" or "claude-done" labels

## Priority Sorting

Urgent (1) > High (2) > Medium (3) > Low (4) > None (0)

## Batch Query

Uses a single GraphQL query that fetches issues with labels, project name, and team inline — minimizes API calls.
