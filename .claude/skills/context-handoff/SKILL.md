---
name: context-handoff
description: Use this skill before compacting, ending a Claude Code session, switching tasks, handing work to another engineer, or resuming work involving SWIRL installation, configuration, scripts, DevUtils, authentication, AI Providers, SearchProviders, RAG, Tika, Docker, or CI/CD workflows.
---

# Context Handoff Skill

## Objective

Create a compact but complete operational handoff that allows another Claude Code session or engineer to safely continue the work without losing important repository context.

This repository may involve several operational domains:

- Local SWIRL community installation.
- Python/Django application setup.
- SQLite or PostgreSQL configuration.
- `.env` configuration.
- OAuth/OIDC/MSAL authentication.
- Microsoft 365 / Microsoft Graph integration.
- SearchProvider configuration.
- AI Provider configuration.
- RAG behavior and distribution strategy.
- Page Fetcher configuration.
- Apache Tika integration.
- DevUtils scripts.
- Docker image build (via GitHub Actions).
- GitHub Actions workflow changes.

The handoff must preserve enough state to continue safely while avoiding secret leakage.

## When to use this skill

Use this skill when:

- The context window is getting large.
- `/compact` will be used.
- A task is paused before completion.
- Another engineer will continue the work.
- Work is moving from investigation to implementation.
- Work is moving from implementation to validation.
- The task involves scripts that can mutate Docker registries, external search indexes, or OAuth providers.
- The task involves `.env`, OIDC, OAuth, API keys, database credentials, or provider configuration.
- The task involves SearchProvider, AI Provider, RAG, Page Fetcher, or Tika configuration.
- The current task produced a partial plan that should not be lost.

## Required safety rules

Never include actual secret values in the handoff.

Do not include:

- API keys.
- OAuth/OIDC client secrets.
- Database passwords.
- Docker registry credentials.
- GitHub PATs or tokens.
- Private keys.
- Session cookies.
- Full `.env` contents.
- Any value that appeared in a sensitive file or command output.

Use placeholders instead:

```text
<redacted>
<stored-in-env>
<api-key-redacted>
<database-password-redacted>
```

If a potentially sensitive value was found, report only:

```md
Sensitive value observed: yes
Action required: verify storage/rotation outside this handoff
```

Do not copy the value.

## Handoff process

Before writing the handoff:

1. Identify the current goal.
2. Identify the affected repository area.
3. Identify files changed or inspected.
4. Identify commands executed.
5. Identify scripts involved.
6. Identify whether the work is local-only or deployment/infrastructure-impacting.
7. Identify whether any secret-bearing files were touched.
8. Identify whether any database, Docker, or external provider action was performed or planned.
9. Identify what was validated.
10. Identify what remains unresolved.

## Required output format

Use this exact structure.

```md
## Goal

Briefly describe what the session was trying to accomplish.

## Current status

State whether the task is:
- Not started
- Investigated only
- Partially implemented
- Implemented but not validated
- Validated locally
- Ready for review
- Blocked

## Repository area

List the affected area(s):

- Local installation
- Python/Django app
- `.env` / runtime config
- SQLite / PostgreSQL / database
- OAuth/OIDC/MSAL
- Microsoft 365 / Microsoft Graph
- SearchProviders
- AI Providers
- RAG
- Page Fetcher
- Apache Tika
- DevUtils
- Docker / GitHub Actions
- Documentation
- Other

## Files changed

List exact changed files.

If no files were changed, write:

No files changed.

## Files inspected

List important inspected files only.

Do not list every file read unless it matters for continuation.

## Commands run

List commands that were actually run.

For each command, include:
- Working directory
- Command
- Result
- Whether it was read-only or mutating

Example:

```text
Working directory: .
Command: python swirl.py config_db
Result: not run / succeeded / failed with <summary>
Type: mutating local database
```

## Scripts involved

List any DevUtils scripts involved.

For each script, include:
- Path
- Purpose
- Whether it is read-only, local-mutating, infrastructure-mutating, or secret-sensitive
- Whether it was run or only inspected

Example:

```text
Path: DevUtils/example.sh
Purpose: <summary>
Risk: infrastructure-mutating
Status: inspected only
```

## Decisions made

List concrete decisions made during the session.

## Assumptions

List assumptions that were made and still need confirmation.

## Installation / local runtime state

Include this section when local setup was involved.

Track:

- Repository cloned: yes/no/unknown
- `./install.sh`: run/not run/failed
- `python swirl.py setup`: run/not run/failed
- `./install-ui.sh -p`: run/not run/failed
- `python swirl.py start`: run/not run/failed
- Local URL: <non-sensitive URL or unknown>

If not applicable, write:

Not applicable.

## Configuration state

Include this section when `.env`, auth, provider, or runtime settings were involved.

Track only non-sensitive names and placeholders.

Relevant examples:

- `DATABASES`: PostgreSQL / SQLite / unknown
- `OIDC_RP_CLIENT_ID`: configured / not configured / placeholder only
- `OIDC_RP_CLIENT_SECRET`: redacted / not inspected
- `MS_AUTH_CLIENT_ID`: configured / not configured / placeholder only
- `MS_TENANT_ID`: configured / not configured / placeholder only
- `MSAL_CB_PORT`: configured / not configured / placeholder only
- `MSAL_HOST`: configured / not configured / placeholder only
- `SWIRL_FQDN`: configured / not configured / placeholder only
- `TIKA_SERVER_ENDPOINT`: configured / not configured / placeholder only
- `SWIRL_RAG_DISTRIBUTION_STRATEGY`: configured / not configured / placeholder only

## Database impact

Include when PostgreSQL, SQLite, migrations, dumps, restores, or data loading were involved.

Track:

- Database engine.
- Database host if non-sensitive.
- Whether migrations/configuration were run.
- Whether data was loaded.
- Whether backup/restore/copy was planned or run.
- Whether destructive database commands were involved.

Never include credentials.

## AI Provider / SearchProvider / RAG impact

Include when provider configuration was involved.

Track:

- AI Provider affected.
- Role affected: `reader`, `query`, `connector`, or `rag`.
- Whether provider was activated/deactivated.
- Whether API keys were involved, redacted.
- SearchProvider affected.
- Page Fetcher configuration affected.
- RAG distribution strategy affected.
- Token/page limits affected.
- Tika dependency affected.

## Docker / CI impact

Include when Docker builds, GitHub Actions workflows, or image publishing were involved.

Track:

- Docker image build/push status.
- Registry target (`swirlai/swirl-search`), if relevant.
- Which GitHub Actions workflow was involved.
- Whether any mutating action (image push, workflow dispatch) was run.
- Whether the action was planned only or executed.

If a mutating action was discussed but not run, explicitly state:

No mutating Docker or CI action was run.

## Validation performed

List validation already performed.

Examples:

- README instructions reviewed.
- Script inspected.
- Command syntax checked.
- Local install command run.
- Django command run.
- Docker build run (no push).
- GitHub Actions workflow reviewed.
- Database connection tested.
- SearchProvider tested.
- AI Provider tested.
- RAG query tested.
- Tika endpoint tested.

If nothing was validated, write:

No validation performed yet.

## Known issues / blockers

List current blockers.

Examples:

- Missing PostgreSQL credentials (if using PostgreSQL instead of default SQLite).
- `.env` incomplete.
- Docker daemon unavailable.
- Tika container not running.
- OIDC callback values unknown.
- SearchProvider API key not configured.
- Potential secret exposure needs review.
- Script has network-mutating behavior and needs approval before execution.

## Risks

List operational/security risks.

Always include this section for work involving scripts, secrets, deployment, database, provider activation, or external integrations.

Examples:

- Running setup commands may mutate the local database.
- AI Provider activation may change runtime LLM behavior.
- SearchProvider changes may affect federated search behavior.
- RAG configuration changes may affect answer quality or token usage.
- Tika misconfiguration may break binary document extraction.
- API key/client secret must not be committed.

## Next steps

List precise next actions.

Each next step should be actionable and scoped.

## Recommended resume prompt

Write a short prompt that can be pasted into the next Claude Code session.

Example:

```text
Continue the SWIRL setup task from the handoff below. First review the files listed under "Files changed" and "Files inspected". Do not run mutating Docker, database, or network commands without explicit approval. Preserve secret redaction rules.
```
```

## Domain-specific guidance

### Local installation handoff

If the task involved local installation, explicitly preserve which install steps were completed.

### OAuth/OIDC/MSAL handoff

If the task involved authentication, report variable names and status only:

```md
- `OIDC_RP_CLIENT_ID`: configured / not configured / placeholder only
- `OIDC_RP_CLIENT_SECRET`: redacted / not inspected
- `MS_AUTH_CLIENT_ID`: configured / not configured / placeholder only
- `MS_TENANT_ID`: configured / not configured / placeholder only
- `MSAL_CB_PORT`: configured / not configured / placeholder only
- `MSAL_HOST`: configured / not configured / placeholder only
```

### AI Provider handoff

If the task involved AI Providers, preserve role and activation details:

```md
- Provider name: <name or unknown>
- Role: reader / query / connector / rag
- Activation change: yes/no
- API key touched: yes, redacted / no
- Model changed: <model or unknown>
- Defaults changed: yes/no/unknown
```

### SearchProvider handoff

If the task involved SearchProviders, preserve:

```md
- SearchProvider: <name or unknown>
- `page_fetch_config_json` changed: yes/no
- Diffbot involved: yes/no
- Microsoft Graph involved: yes/no
- Tika required: yes/no
- Timeout/cache/header behavior changed: yes/no
```

### RAG / Tika handoff

If the task involved RAG or Tika, preserve:

```md
- `SWIRL_RAG_DISTRIBUTION_STRATEGY`: Distributed / RoundRobin / Sorted / unknown
- `SWIRL_RAG_MODEL`: <model or unknown>
- `SWIRL_RAG_TOK_MAX`: <value or unknown>
- `SWIRL_RAG_MAX_TO_CONSIDER`: <value or unknown>
- `TIKA_SERVER_ENDPOINT`: configured / not configured / placeholder only
- Tika container running: yes/no/unknown
```

### DevUtils handoff

If the task involved scripts, preserve script-level risk classification:

```md
| Script | Purpose | Risk | Status |
|---|---|---|---|
| `<path>` | `<summary>` | read-only / local-mutating / networked / secret-sensitive | inspected / run / not run |
```

Risk classification:

- `read-only`: prints, checks, renders, or inspects.
- `local-mutating`: modifies local files, local database, or local environment.
- `networked`: calls external services, indexes remote data, or connects to search backends.
- `secret-sensitive`: reads, writes, prints, transforms, or depends on credentials, API keys, tokens, or private configuration.

## Final quality checklist

Before returning the handoff, verify:

- [ ] No secret values are included.
- [ ] Exact files changed are listed.
- [ ] Commands are listed with working directory and result.
- [ ] Script paths are listed if scripts were involved.
- [ ] Mutating actions are clearly labeled.
- [ ] Validation status is explicit.
- [ ] Known blockers are explicit.
- [ ] Next steps are actionable.
- [ ] A recommended resume prompt is included.
