---
name: scan
description: Run the full NightShift pipeline — scan Linear for eligible tickets and process them
---

# /scan

Run the full NightShift pipeline.

## Usage
```
/scan
```

## What It Does

1. Connects to Linear API
2. Fetches tickets in "Ready for Development" assigned to you
3. Sorts by priority (Urgent first)
4. For each ticket:
   - Parses Pathfinder RCA/TRD comment
   - Clones/updates target repos
   - Runs Test Agent (writes tests)
   - Runs Dev Agent (implements fix)
   - Creates PR to dev
   - Moves ticket to "Code Review"

## Execution

```bash
docker exec nightshift python3 engine/run_once.py
```

## Expected Output

```
=== Starting ticket scan ===
Authenticated as: user@ruh.ai
Sentinel Guardian: enabled (13 skills available)
Scanning team: Ruh (RUH)
Eligible tickets (2): RUH-384(High), RUH-385(Medium)
[RUH-384] Pathfinder repos: ['agent-platform-v2']
[RUH-384] Starting Test Agent...
[RUH-384] Test Agent complete — tests committed.
[RUH-384] Starting Dev Agent...
[RUH-384] Dev Agent complete.
Done: RUH-384 -> https://github.com/ruh-ai/agent-platform-v2/pull/42
=== Scan complete ===
```
