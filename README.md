# NightShift :crescent_moon:

> Autonomous development agent — picks up tickets, writes tests, implements fixes, ships PRs while you sleep.

An OpenClaw agent that processes Linear tickets end-to-end using Test-Driven Development with Sentinel Guardian test methodology.

## How It Works

```
Pathfinder analyzes ticket → adds RCA/TRD → moves to "Ready for Development"
  |
  v
NightShift picks it up
  |
  +-- Collects eligible tickets, sorts by priority
  +-- Parses Pathfinder comment (repos, file hints, code changes)
  +-- Clones/updates repos in parallel
  |
  +-- Test Agent (1 Claude Code session per repo)
  |     Detects stack (backend/frontend/fullstack)
  |     Loads Sentinel Guardian test skills
  |     Writes tests for all layers
  |     Commits: test(RUH-384): add tests
  |
  +-- Dev Agent (1 Claude Code session per repo)
  |     Reads Pathfinder RCA/TRD as primary context
  |     Implements fix until ALL tests pass
  |     NEVER edits test files
  |     Commits: fix(RUH-384): increase timeout to 240s
  |
  +-- Creates PR to dev
  +-- Comments review summary on Linear ticket
  +-- Moves ticket to "Code Review"
```

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

## Project Structure

```
NightShift/
|-- IDENTITY.md              # Agent identity
|-- SOUL.md                  # Core behavior + hard rules
|-- ARCHITECTURE.md          # System design
|-- TOOLS.md                 # Available tools
|-- AGENTS.md                # Sub-agent overview
|-- agents/                  # OpenClaw agent definitions
|   |-- test-agent.md
|   +-- dev-agent.md
|-- skills/                  # OpenClaw skill definitions
|   |-- ticket-scanner/
|   |-- pathfinder-reader/
|   |-- test-generator/
|   |-- implementer/
|   +-- pr-creator/
|-- commands/                # OpenClaw chat commands
|   |-- scan.md
|   |-- status.md
|   +-- check.md
|-- engine/                  # Python execution engine
|   |-- lib/
|   |   |-- config.py
|   |   |-- core.py
|   |   +-- linear_client.py
|   |-- skills/
|   |   |-- ticket_enricher.py
|   |   |-- developer_skill.py
|   |   |-- sentinel_integration.py
|   |   +-- pathfinder_parser.py
|   |-- main.py
|   +-- run_once.py
|-- Dockerfile
|-- docker-compose.yml
|-- entrypoint.sh
|-- requirements.txt
+-- .env.example
```

## Commands

| Command | What it does |
|---------|-------------|
| `scan` | Run the full pipeline |
| `status` | Show container logs |
| `check RUH-XXX` | Check specific ticket |
