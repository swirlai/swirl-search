# Claude Code Structure

This directory defines the Claude Code operating model for this repository.

## Included components

| Path | Purpose |
|---|---|
| `agents/` | Specialized review agents |
| `commands/` | Custom slash command prompts for common tasks |
| `skills/` | Reusable workflows for install, DevUtils, Docker, RAG/search, and handoffs |
| `rules/` | Repository-specific guardrails |
| `settings.example.json` | Conservative local permission example; copy it to `settings.local.json` (gitignored). Bash rules match command prefixes only, so the deny list is advisory: destructive SQL, image pushes and similar are governed by the explicit-approval rules in `CLAUDE.md`, not by this file. |

## Setup

Copy the example settings to initialize local Claude permissions:

```bash
cp .claude/settings.example.json .claude/settings.local.json
```

## Recommended workflows

```text
/local-install-plan
/devutils-script-review
/docker-image-build-plan
/search-provider-and-rag-review
/context-handoff
```

## Safety posture

This repository includes scripts that can mutate Docker registries, local environments, and external search indexes. Treat execution as high-risk unless the script is explicitly read-only or dry-run.
