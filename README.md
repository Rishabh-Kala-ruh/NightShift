# NightShift 🌙

> Autonomous development agent — picks up tickets, writes tests, implements fixes, ships PRs while you sleep.

An OpenClaw agent that processes Linear tickets end-to-end using Test-Driven Development with Sentinel Guardian test methodology.

---

## End-to-End Flow

### The Big Picture

```
 Linear Board                  Pathfinder (upstream)               NightShift (this agent)
 ───────────                   ────────────────────               ──────────────────────────
 Ticket created        →       Analyzes ticket                    
 in "Todo" / "Backlog"         Writes RCA (bug) or TRD (feature)  
                               Adds comment with analysis          
                               Moves to "Ready for Development"  → Picks up ticket
                                                                   Filters repos (LLM)
                                                                   Writes tests (Sentinel)
                                                                   Implements fix (TDD)
                                                                   Pushes branch + creates PR
                                                                   Moves to "Code Review"
```

### Detailed Pipeline (6 Phases)

#### Phase 1: COLLECT — Find eligible tickets

```
Linear API
  │
  ├─ Fetch all tickets in "Ready for Development" status
  ├─ Exclude already-processed tickets (tracked in processed_issues.json)
  ├─ Exclude tickets with "claude-processing" or "claude-done" labels
  └─ Sort by priority: Urgent → High → Medium → Low → None
```

NightShift authenticates with the Linear API, scans every team the API key has access to, and collects eligible tickets. Priority sorting ensures the most critical work happens first.

#### Phase 2: PREPARE — Parse analysis & prepare repos

```
For each ticket:
  │
  ├─ Fetch all comments from Linear
  ├─ Find Pathfinder comment (contains RCA or TRD)
  ├─ Parse Pathfinder analysis:
  │     ├─ Classification (BUG / FEATURE / TASK)
  │     ├─ Complexity (S / M / L / XL)
  │     ├─ Repos affected (with notes: "Primary Changes", "No Changes Needed", etc.)
  │     ├─ Code changes table (file, function, change type, description)
  │     └─ File hints (paths mentioned in analysis)
  │
  ├─ 🆕 LLM Repo Filter (repo_filter.py)
  │     ├─ Sends full Pathfinder text + repo list to Claude CLI
  │     ├─ Asks: "Which repos actually need code changes?"
  │     ├─ Filters out repos that need no modifications
  │     ├─ Handles any phrasing (not string-matching)
  │     ├─ 30s timeout, falls back to all repos on failure
  │     └─ Logs which repos were filtered out and why
  │
  ├─ Enrich ticket context:
  │     ├─ Sub-issues and their statuses
  │     ├─ Related issues (blocks, blocked by, duplicates)
  │     ├─ Acceptance criteria extraction
  │     └─ Attachment URLs
  │
  └─ Clone/update filtered repos in parallel (up to 4 at once)
        ├─ Auto-clone from git@github.com:{org}/{repo}.git if not cached
        ├─ Pull latest from target branch (dev/main/master)
        └─ Create isolated git worktree: .worktrees/claude/{ticket-id}
```

**Why filter repos?** Pathfinder lists all repos it analyzed, including ones that explicitly need no changes (e.g., "communication-service — No Changes Needed ✅"). Without filtering, NightShift would waste two Claude Code sessions (Test Agent + Dev Agent) per unnecessary repo, creating junk test-only PRs.

#### Phase 3: SCOPE — Resolve ticket type and context

```
Ticket Scope Resolution:
  │
  ├─ "normal" — standalone ticket, no children
  │     └─ Process normally
  │
  ├─ "parent_with_subtasks" — has child issues
  │     ├─ Identify sub-tasks assigned to OTHER developers
  │     ├─ Exclude their scope from implementation
  │     └─ Only implement unassigned scope + own sub-tasks
  │
  └─ "subtask" — is a child of a parent ticket
        ├─ Fetch parent ticket for context
        └─ Only implement THIS sub-task's scope (not the parent)
```

Scope resolution prevents NightShift from stepping on other developers' work when processing tickets with sub-tasks.

#### Phase 4: TEST — Write tests first (Test Agent)

```
For each filtered repo:
  │
  ├─ Detect stack: backend / frontend / fullstack
  │     (inspects package.json, requirements.txt, go.mod, etc.)
  │
  ├─ Load Sentinel Guardian test skills for detected stack:
  │     ├─ Unit tests (pytest / jest / go test)
  │     ├─ Integration tests
  │     ├─ API contract tests
  │     ├─ Security tests
  │     └─ ... (13 skills total)
  │
  ├─ Build test prompt:
  │     ├─ Ticket description + acceptance criteria
  │     ├─ Pathfinder analysis (RCA/TRD)
  │     ├─ File hints (where to look)
  │     ├─ Existing test patterns in the repo
  │     └─ All relevant Sentinel skill instructions (concatenated)
  │
  └─ Spawn Claude Code session (Test Agent):
        ├─ Reads the codebase
        ├─ Writes test cases covering:
        │     ├─ Main fix/feature behavior
        │     ├─ Each acceptance criterion
        │     └─ Edge cases from discussion comments
        ├─ Commits: test(RUH-XXX): add tests for <summary>
        └─ Max 30 turns, 15-minute timeout
```

**Key rule:** Tests are written BEFORE implementation. They define the contract. The Dev Agent must make them pass without modifying test files.

#### Phase 5: IMPLEMENT — Make tests pass (Dev Agent)

```
For each filtered repo (same worktree as Test Agent):
  │
  ├─ Build implementation prompt:
  │     ├─ Pathfinder RCA/TRD as primary source of truth
  │     ├─ 🆕 Code changes scoped to current repo only
  │     │     ├─ "Code Changes for This Repo" — what to modify
  │     │     └─ "Code Changes in Other Repos" — read-only context
  │     ├─ Scope restrictions (sub-task exclusions)
  │     ├─ Discussion thread (clarifications, decisions)
  │     └─ Developer skill instructions (TDD workflow)
  │
  └─ Spawn Claude Code session (Dev Agent):
        ├─ Reads test files committed by Test Agent
        ├─ Runs tests — confirms they FAIL (red)
        ├─ Implements the fix/feature following Pathfinder's code changes table
        ├─ Runs tests — iterates until they PASS (green)
        ├─ Runs full test suite — checks for regressions
        ├─ Commits: fix(RUH-XXX): <what was changed>
        └─ NEVER edits test files
```

**Critical rules:**
- Tests are the contract — if code doesn't pass, fix the code, not the tests
- Follow Pathfinder's code changes table precisely
- Minimal changes — don't refactor unrelated code
- If unable to fix, creates `CLAUDE_UNABLE.md` explaining why

#### Phase 6: SHIP — Push, PR, and transition

```
For each repo with commits:
  │
  ├─ Verify changes exist (git diff)
  ├─ Check for CLAUDE_UNABLE.md (skip if present)
  ├─ Push branch: claude/{ticket-id} → origin
  ├─ Create GitHub PR:
  │     ├─ Base: dev (configurable via TARGET_BRANCH)
  │     ├─ Title: fix(RUH-XXX): <ticket title>
  │     └─ Body: ticket description + Linear URL
  └─ Clean up worktree
  
After all repos:
  │
  ├─ Comment on Linear ticket:
  │     "🤖 Claude Code created N PR(s): [links]"
  ├─ Transition ticket to "Code Review"
  └─ Mark as processed (won't pick up again)
```

### Visual Flow Summary

```
┌─────────────────────────────────────────────────────────────────────┐
│                        NightShift Pipeline                          │
│                                                                     │
│  ┌──────────┐   ┌───────────┐   ┌──────────┐   ┌────────────────┐ │
│  │ COLLECT  │──>│  PREPARE  │──>│  SCOPE   │──>│   Per Repo:    │ │
│  │          │   │           │   │          │   │                │ │
│  │ Linear   │   │ Pathfinder│   │ Normal / │   │ ┌────────────┐│ │
│  │ tickets  │   │ parse +   │   │ Parent / │   │ │ TEST AGENT ││ │
│  │ sorted   │   │ LLM repo  │   │ Subtask  │   │ │ (Sentinel) ││ │
│  │ by       │   │ filter +  │   │ context  │   │ └─────┬──────┘│ │
│  │ priority │   │ clone     │   │          │   │       │       │ │
│  └──────────┘   └───────────┘   └──────────┘   │ ┌─────▼──────┐│ │
│                                                  │ │ DEV AGENT  ││ │
│                                                  │ │ (TDD impl) ││ │
│                                                  │ └─────┬──────┘│ │
│                                                  │       │       │ │
│                                                  │ ┌─────▼──────┐│ │
│                                                  │ │ PUSH + PR  ││ │
│                                                  │ └────────────┘│ │
│                                                  └────────────────┘ │
│                                                          │          │
│                                              ┌───────────▼────────┐ │
│                                              │ Comment on Linear  │ │
│                                              │ Move to Code Review│ │
│                                              └────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### Linear Ticket Lifecycle

```
  Backlog / Todo
       │
       ▼
  Pathfinder analyzes
       │
       ▼
  Ready for Development  ◄── NightShift picks up here
       │
       ▼
  In Progress            ◄── NightShift moves here when starting
       │
       ▼
  Code Review            ◄── NightShift moves here when PR is created
       │
       ▼
  Ready to Deploy - DEV  ◄── After human review approval
       │
       ▼
  (QA → Prod flow)
```

---

## Key Components

### Pathfinder Parser (`engine/skills/pathfinder_parser.py`)
Extracts structured data from Pathfinder's analysis comments:
- Classification (BUG/FEATURE), complexity (S/M/L/XL)
- Affected repos with contextual notes ("Primary Changes", "No Changes Needed")
- Code changes table (file → function → change type)
- File hints for investigation starting points

### LLM Repo Filter (`engine/skills/repo_filter.py`)
Lightweight Claude CLI call that reads the full Pathfinder analysis and determines which repos actually need code changes. Uses semantic understanding — not string matching — so it handles any phrasing Pathfinder might use.

### Developer Skill (`engine/skills/developer_skill.py`)
Intelligence layer between ticket fetching and Claude Code execution:
- Resolves ticket scope (normal / parent with subtasks / subtask)
- Enriches context with sub-issues, relations, acceptance criteria
- Builds repo-scoped prompts for Test Agent and Dev Agent

### Sentinel Integration (`engine/skills/sentinel_integration.py`)
Loads Sentinel Guardian test skills based on detected stack:
- Detects backend/frontend/fullstack from project files
- Concatenates relevant skill instructions into a single test prompt
- 13 test skills covering unit, integration, API, security, etc.

### Ticket Enricher (`engine/skills/ticket_enricher.py`)
Deep context extraction from Linear:
- Discussion thread (all comments with authors and dates)
- Sub-issues and their statuses
- Related issues (blocking/blocked-by/duplicates)
- Acceptance criteria parsing
- File hints from descriptions and comments

### Core Orchestrator (`engine/lib/core.py`)
Three-phase processing engine:
- **Phase 1 (COLLECT):** Fetch, filter, sort tickets
- **Phase 2 (PREPARE):** Parse Pathfinder, filter repos, clone in parallel
- **Phase 3 (EXECUTE):** Process tickets in parallel (configurable concurrency)

---

## OpenClaw Integration

```bash
# Register as OpenClaw agent
openclaw agents add nightshift --workspace ~/NightShift --non-interactive

# Chat with NightShift
openclaw tui --session nightshift

# Run via agent command
openclaw agent --agent nightshift -m "scan for tickets" --timeout 3600

# Schedule hourly scans
openclaw cron add --name nightshift-scan --every 1h \
  --message "docker exec nightshift python3 engine/run_once.py" \
  --timeout 3600000
```

---

## Quick Start

### 1. Clone and Configure

```bash
git clone https://github.com/Rishabh-Kala-ruh/NightShift.git
cd NightShift
cp .env.example .env
# Edit .env with your credentials
```

### 2. Deploy to Server

```bash
ssh user@your-server
cd NightShift
docker compose up -d --build

# Authenticate Claude Code (one-time)
docker exec -it nightshift claude setup-token

# Verify
docker exec nightshift claude auth status
docker logs nightshift --tail 20
```

### 3. Register with OpenClaw

```bash
openclaw agents add nightshift --workspace ~/NightShift --non-interactive
```

---

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `LINEAR_API_KEY` | Linear API key | Required |
| `GITHUB_ORG` | GitHub organization | `ruh-ai` |
| `TARGET_BRANCH` | Base branch for PRs | `dev` |
| `GH_TOKEN` | GitHub Personal Access Token | Required |
| `CLAUDE_CODE_OAUTH_TOKEN` | Claude Code OAuth token | Required |
| `MAX_CONCURRENT_TICKETS` | Parallel ticket limit | `2` |
| `POLL_INTERVAL_MINUTES` | Scan frequency | `60` |
| `SENTINEL_SKILLS_PATH` | Sentinel Guardian skills | Auto-detected |

---

## Project Structure

```
NightShift/
├── IDENTITY.md              # Agent identity
├── SOUL.md                  # Core behavior + hard rules
├── ARCHITECTURE.md          # System design
├── TOOLS.md                 # Available tools
├── AGENTS.md                # Sub-agent overview
├── agents/                  # OpenClaw agent definitions
│   ├── test-agent.md
│   └── dev-agent.md
├── skills/                  # OpenClaw skill definitions
│   ├── ticket-scanner/
│   ├── pathfinder-reader/
│   ├── test-generator/
│   ├── implementer/
│   └── pr-creator/
├── commands/                # OpenClaw chat commands
│   ├── scan.md
│   ├── status.md
│   └── check.md
├── engine/                  # Python execution engine
│   ├── lib/
│   │   ├── config.py        # Environment config loader
│   │   ├── core.py          # 3-phase orchestrator
│   │   └── linear_client.py # Linear GraphQL API client
│   ├── skills/
│   │   ├── ticket_enricher.py       # Deep ticket context extraction
│   │   ├── developer_skill.py       # Scope resolution + prompt building
│   │   ├── sentinel_integration.py  # Sentinel skill loading + stack detection
│   │   ├── pathfinder_parser.py     # Pathfinder comment parser
│   │   └── repo_filter.py          # LLM-based repo filtering
│   ├── main.py              # Continuous loop mode
│   └── run_once.py          # Single-scan mode
├── Dockerfile
├── docker-compose.yml
├── entrypoint.sh
├── requirements.txt
└── .env.example
```

---

## Commands

| Command | What it does |
|---------|-------------|
| `scan` | Run the full pipeline |
| `status` | Show container logs |
| `check RUH-XXX` | Check specific ticket |
