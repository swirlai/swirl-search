# Claude Code Structure

This directory defines the Claude Code operating model for this repository.

## Included components

| Path | Purpose |
|---|---|
| `agents/` | Specialized review agents |
| `commands/` | Custom slash command prompts for common tasks |
| `skills/` | Reusable workflows for install, DevUtils, Docker, RAG/search, and handoffs |
| `rules/` | Repository-specific guardrails |
| `settings.example.json` | Conservative local permission example |

## Setup

Copy the example settings to initialize local Claude permissions:

```bash
cp .claude/settings.example.json .claude/settings.json
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
