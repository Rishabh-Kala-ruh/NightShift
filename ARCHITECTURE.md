# ARCHITECTURE.md — NightShift

## System Overview

```
                   Linear Board
                       |
          Pathfinder   |   NightShift
          (upstream)   |   (this agent)
               |       |       |
               v       v       v
          +---------+     +-----------+
          | Analyze |     | Collect   |  Fetch "Ready for Development" tickets
          | ticket  |     | & Sort    |  from Linear API
          +---------+     +-----------+
               |               |
               v               v
          +---------+     +-----------+
          | Add RCA |     | Prepare   |  Parse Pathfinder, clone repos,
          | or TRD  |     | Repos     |  create worktrees
          +---------+     +-----------+
               |               |
               v               v
          +---------+     +-----------+     +------------------+
          | Move to |     | Test      |---->| Test Generator   |
          | Ready   |     | Agent     |     | (unit, integ,    |
          | for Dev |     |           |     |  security, etc.) |
          +---------+     +-----------+     +------------------+
                               |
                               v
                          +-----------+     +------------------+
                          | Dev       |---->| Pathfinder       |
                          | Agent     |     | RCA/TRD context  |
                          +-----------+     +------------------+
                               |
                               v
                          +-----------+
                          | PR + Move |  Push, create PR, comment,
                          | to Review |  move to "Code Review"
                          +-----------+
```

## Directory Structure

```
NightShift/
|-- IDENTITY.md              # Agent identity (name, emoji, vibe)
|-- SOUL.md                  # Core behavior, pipeline, hard rules
|-- ARCHITECTURE.md          # This file — system design
|-- TOOLS.md                 # Available tools and commands
|-- AGENTS.md                # Sub-agent definitions overview
|
|-- agents/                  # Sub-agent definitions (OpenClaw format)
|   |-- test-agent.md        # Test Agent — writes tests via built-in skill
|   +-- dev-agent.md         # Dev Agent — implements fixes via TDD
|
|-- skills/                  # Skill definitions (OpenClaw format)
|   |-- ticket-scanner/SKILL.md      # Fetch & filter Linear tickets
|   |-- pathfinder-reader/SKILL.md   # Parse Pathfinder RCA/TRD comments
|   |-- test-generator/SKILL.md      # Built-in multi-layer test methodology
|   |-- implementer/SKILL.md         # Implement fix using TDD
|   +-- pr-creator/SKILL.md          # Push branch and create PR
|
|-- commands/                # Chat commands (OpenClaw format)
|   |-- scan.md              # /scan — run the full pipeline
|   |-- status.md            # /status — show recent logs
|   +-- check.md             # /check <ticket> — check specific ticket
|
|-- engine/                  # Python execution engine
|   |-- lib/                 # Core library
|   |   |-- config.py        # Environment config loader
|   |   |-- core.py          # 3-phase orchestrator
|   |   +-- linear_client.py # Linear GraphQL API client
|   |-- skills/              # Python skill implementations
|   |   |-- ticket_enricher.py       # Deep ticket context extraction
|   |   |-- developer_skill.py       # Scope resolution + prompt building
|   |   |-- test_prompt_builder.py   # Test prompt building + stack detection
|   |   +-- pathfinder_parser.py     # Pathfinder comment parser
|   |-- main.py              # Continuous loop mode
|   +-- run_once.py          # Single-scan mode
|
|-- Dockerfile               # Container image
|-- docker-compose.yml       # Container orchestration
|-- entrypoint.sh            # Container startup
|-- requirements.txt         # Python dependencies
|-- .env.example             # Config template
+-- .gitignore
```

## Key Design Decisions

### Skills vs Agents
- **Skills** are knowledge documents — they describe HOW to do something
- **Agents** READ skills and DO the work
- Test Agent reads the test-generator skill to know HOW to write tests, then writes them
- Dev Agent reads the developer skill to know HOW to implement, then implements

### Two Claude Code Sessions Per Repo
- Test Agent: one session with all relevant test layers from the built-in skill
- Dev Agent: one session with Pathfinder RCA/TRD + developer skill instructions

### Pathfinder as Primary Context
- Pathfinder comments contain exact root cause analysis (bugs) or technical design (features)
- Includes code changes table: exact files, functions, change types
- NightShift uses this as the primary source of truth for repo detection and implementation

### Docker-Based Execution
- The Python engine runs inside a Docker container
- Repos are cloned into persistent Docker volumes
- Claude Code CLI runs inside the container with OAuth token auth
