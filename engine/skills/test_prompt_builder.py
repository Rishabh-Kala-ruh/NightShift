"""
Test Prompt Builder — loads the built-in test-generator skill and builds
prompts for the Test Agent.

All test methodology lives in skills/test-generator/SKILL.md (no external dependency).

Usage:
    from skills.test_prompt_builder import TestPromptBuilder

    builder = TestPromptBuilder()
    prompt = builder.build_test_prompt(enriched_context, worktree_path, repo_name)
"""

from __future__ import annotations

import json
import os
from typing import Any

from skills.ticket_enricher import EnrichedContext


# ── Skill chains by stack type ───────────────────────────────────────────────

BACKEND_LAYERS = [
    "unit", "integration", "contract", "security", "resilience", "e2e-api",
]

FRONTEND_LAYERS = [
    "unit", "e2e-browser",
]

FULLSTACK_LAYERS = [
    "unit", "integration", "contract", "security", "resilience",
    "e2e-api", "e2e-browser",
]


# ── Stack detection signals ──────────────────────────────────────────────────

BACKEND_SIGNALS = [
    "requirements.txt", "pyproject.toml", "setup.py", "Pipfile",  # Python
    "go.mod",       # Go
    "Cargo.toml",   # Rust
    "pom.xml", "build.gradle",  # Java
    "Gemfile",      # Ruby
]

FRONTEND_SIGNALS = [
    "next.config.js", "next.config.ts", "next.config.mjs",  # Next.js
    "vite.config.ts", "vite.config.js",  # Vite
    "angular.json",      # Angular
    "svelte.config.js",  # Svelte
    "nuxt.config.ts",    # Nuxt
]

FRONTEND_DEPS = {"react", "next", "vue", "angular", "svelte", "nuxt"}


# ── Smart layer selection triggers ───────────────────────────────────────────

_LAYER_TRIGGERS: dict[str, list[str]] = {
    "contract":    ["api/", "routes/", "endpoint", "openapi", "schema", "swagger", "graphql"],
    "security":    ["auth", "permission", "middleware", "token", "session", "password", "rbac", "oauth", "jwt"],
    "resilience":  ["retry", "timeout", "circuit", "fallback", "client/", "http", "grpc", "queue"],
    "e2e-api":     ["api/", "routes/", "endpoint", "handler", "controller", "view"],
    "e2e-browser": ["page", "component", "view", "screen", "layout", "modal"],
}

# Always included regardless of file changes
_ALWAYS_INCLUDE = {"unit", "integration"}


# ── Skill / Agent loading ────────────────────────────────────────────────────

_SKILL_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "skills", "test-generator")
)
_AGENT_DIR = os.path.join(os.path.dirname(__file__), "agents")

_skill_cache: str | None = None
_agent_cache: str | None = None


def _load_skill_md() -> str:
    """Load skills/test-generator/SKILL.md. Cached after first read."""
    global _skill_cache
    if _skill_cache is not None:
        return _skill_cache

    skill_file = os.path.join(_SKILL_DIR, "SKILL.md")
    if os.path.exists(skill_file):
        with open(skill_file) as f:
            content = f.read()
        # Strip YAML frontmatter
        if content.startswith("---"):
            end = content.find("---", 3)
            if end != -1:
                content = content[end + 3:].strip()
        _skill_cache = content
    else:
        _skill_cache = ""

    return _skill_cache


def _load_agent_md() -> str:
    """Load engine/skills/agents/test-agent.md. Cached after first read."""
    global _agent_cache
    if _agent_cache is not None:
        return _agent_cache

    agent_file = os.path.join(_AGENT_DIR, "test-agent.md")
    if os.path.exists(agent_file):
        with open(agent_file) as f:
            content = f.read()
        if content.startswith("---"):
            end = content.find("---", 3)
            if end != -1:
                content = content[end + 3:].strip()
        _agent_cache = content
    else:
        _agent_cache = ""

    return _agent_cache


# ── Test Prompt Builder ──────────────────────────────────────────────────────


class TestPromptBuilder:
    """Builds test-generation prompts using the built-in test skill."""

    def detect_stack(self, worktree_path: str) -> str:
        """
        Detect repo stack type by checking for signal files.
        Returns: "backend", "frontend", or "fullstack"
        """
        has_backend = False
        has_frontend = False

        for signal in BACKEND_SIGNALS:
            if os.path.exists(os.path.join(worktree_path, signal)):
                has_backend = True
                break

        for signal in FRONTEND_SIGNALS:
            if os.path.exists(os.path.join(worktree_path, signal)):
                has_frontend = True
                break

        # Check package.json for frontend deps if not already detected
        if not has_frontend:
            pkg_json = os.path.join(worktree_path, "package.json")
            if os.path.exists(pkg_json):
                try:
                    with open(pkg_json) as f:
                        pkg = json.load(f)
                    all_deps: set[str] = set()
                    all_deps.update((pkg.get("dependencies") or {}).keys())
                    all_deps.update((pkg.get("devDependencies") or {}).keys())
                    if all_deps & FRONTEND_DEPS:
                        has_frontend = True
                    # package.json without frontend deps → Node.js backend
                    if not has_frontend and not has_backend:
                        has_backend = True
                except Exception:
                    pass

        if has_backend and has_frontend:
            return "fullstack"
        if has_frontend:
            return "frontend"
        if has_backend:
            return "backend"

        return "backend"  # default

    def get_layers(self, stack: str) -> list[str]:
        """Get applicable test layers for a stack type."""
        if stack == "fullstack":
            return list(FULLSTACK_LAYERS)
        if stack == "frontend":
            return list(FRONTEND_LAYERS)
        return list(BACKEND_LAYERS)

    def select_layers_for_changes(
        self, base_layers: list[str], file_changes: list[Any], repo_name: str,
    ) -> list[str]:
        """
        Pick only the test layers relevant to actual code changes.

        Always includes: unit, integration (core layers).
        Specialized layers (contract, security, resilience, etc.) only included
        if the changed files/descriptions match their trigger keywords.
        """
        selected = set(_ALWAYS_INCLUDE)

        # Collect search text from file changes scoped to this repo
        search_parts: list[str] = []
        for fc in file_changes:
            if hasattr(fc, "repo") and fc.repo and fc.repo != repo_name:
                continue
            for attr in ("file", "description", "function"):
                val = getattr(fc, attr, None)
                if val:
                    search_parts.append(val.lower())
        search_text = " ".join(search_parts)

        # Check triggers
        for layer, keywords in _LAYER_TRIGGERS.items():
            if layer in base_layers and any(kw in search_text for kw in keywords):
                selected.add(layer)

        # Preserve original ordering
        return [l for l in base_layers if l in selected]

    def build_test_prompt(
        self,
        context: EnrichedContext,
        worktree_path: str,
        repo_name: str,
        pathfinder: Any | None = None,
    ) -> str:
        """
        Build a comprehensive test prompt for the Test Agent.

        Combines: test-agent.md + ticket context + test-generator SKILL.md
        Scoped to the ticket's actual code changes via smart layer selection.
        """
        stack = self.detect_stack(worktree_path)
        base_layers = self.get_layers(stack)

        # Smart layer selection based on Pathfinder file changes
        if pathfinder and hasattr(pathfinder, "file_changes") and pathfinder.file_changes:
            layers = self.select_layers_for_changes(base_layers, pathfinder.file_changes, repo_name)
        else:
            layers = base_layers

        agent_md = _load_agent_md()
        skill_md = _load_skill_md()

        sections: list[str] = []

        # Agent definition
        if agent_md:
            sections.append(agent_md)
            sections.append("")

        # Header
        sections.append(f"# Test Generation for {context.id} — {context.title}")
        sections.append(f"**Repo:** `{repo_name}` at `{worktree_path}`")
        sections.append(f"**Stack:** {stack}")
        sections.append(f"**Test layers to generate:** {', '.join(layers)}")

        # Scope from Pathfinder
        if pathfinder and hasattr(pathfinder, "file_changes") and pathfinder.file_changes:
            repo_changes = [fc for fc in pathfinder.file_changes if not fc.repo or fc.repo == repo_name]
            if repo_changes:
                sections.append("\n## Scope: Test ONLY These Changes")
                sections.append("> Write tests specifically for these files and functions. "
                                "Do NOT write tests for unrelated parts of the codebase.\n")
                for fc in repo_changes:
                    sections.append(f"- **{fc.change_type}** `{fc.file}` → `{fc.function}` — {fc.description}")
                sections.append("")

        # Ticket context
        sections.append(f"\n{self._build_ticket_context(context)}")

        # Test skill methodology
        if skill_md:
            sections.append("\n---\n")
            sections.append(skill_md)

        # Final rules
        sections.append(f"""
---
## CRITICAL RULES

1. **ONLY write tests.** Do NOT implement the fix/feature. Do NOT modify source code.
2. **ONLY test the specific changes** from the Scope section above. Do NOT test unrelated functionality.
3. **Every acceptance criterion** must have at least one corresponding test.
4. **Edge cases from comments** must be tested.
5. **Follow the repo's existing test conventions** — same framework, directory structure, fixtures.
6. **No catch-all test files** — tests go in module-aligned files.
7. **Verify mock targets exist** before mocking them.
8. **Commit all test files** with message: `{context.id} Add tests for {context.title}`
9. **Run the tests** after committing. They SHOULD fail (no implementation yet).
10. **Never create or modify GitHub workflow files** or CI/CD configs.
11. Do NOT push. Do NOT create a PR. Just commit locally.
""")

        return "\n".join(sections)

    def _build_ticket_context(self, context: EnrichedContext) -> str:
        """Build the ticket context section for the prompt."""
        sections: list[str] = []

        sections.append("## Ticket Context")
        sections.append(f"**ID:** {context.id}")
        sections.append(f"**Title:** {context.title}")
        sections.append(f"**Priority:** {context.priority}")
        sections.append(f"**Description:**\n{context.description}")

        if context.acceptance_criteria:
            sections.append("\n### Acceptance Criteria (EACH must have at least one test)")
            for i, ac in enumerate(context.acceptance_criteria, 1):
                sections.append(f"{i}. {ac}")

        if context.comments:
            sections.append(f"\n### Discussion Thread (check for edge cases to test)")
            for c in context.comments:
                date = c.created_at[:10] if c.created_at else "unknown"
                sections.append(f"\n**{c.author}** ({date}):\n{c.body}")

        if context.file_hints:
            sections.append("\n### Likely Relevant Files")
            for f in context.file_hints:
                sections.append(f"- `{f}`")

        return "\n".join(sections)
