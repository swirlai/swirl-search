# CLAUDE.md

Operating guide for Claude Code in the SWIRL Community (`swirl-search`) backend.

## What SWIRL is

Federated search engine with RAG. NLP plus embeddings re-rank results from many sources, and data stays in its original location (OneDrive, Box, databases, search engines, and so on). The current focus is better access to enterprise data than a straight per-repo MCP search would give.

The SWIRL Assistant (chat plus RAG over federated results) is in scope and drives the federated-SQL demo work. Do not treat the assistant as discontinued.

## Working conventions

### Branching and releases

- All work happens on feature or fix branches.
- Feature/fix branches merge to `develop`. Documentation branches merge to `main`.
- `develop` merges to `main` only as part of a release.
- Never push directly to `main`. Push a feature branch to its same-name remote. Ask if ambiguous.
- Claude pushes to feature/fix branches and gives the user the PR URL. The user merges.

### The two repos

- Backend/core: `swirl-search` (this repo).
- Frontend: `swirl-galaxy` (distributed as `swirlai/spyglass` Docker image). `install-ui.sh` pulls the image and copies the built assets into `static/galaxy/`.
- Cross-cutting features may need changes in both repos.

### Galaxy UI install (the top "it's not working" trap)

Two layers, do not confuse them:

| Layer  | Path                    | What                           |
|--------|-------------------------|--------------------------------|
| Built  | Docker image (pulled)   | `swirlai/spyglass` or `--preview` |
| Served | `static/galaxy/`        | what Django serves             |

Running `./install-ui.sh` (or `./install-ui.sh -p` for preview) pulls the image and copies assets into `static/galaxy/`. Editing nothing in this repo changes the UI — the source lives in `swirl-galaxy`. Hard-refresh (Cmd-Shift-R) after install. For local testing, use `-p` (preview) unless on a release branch.

### URL routing

`swirl.urls` is mounted under two prefixes in `swirl_server/urls.py`: `/swirl/...` and
`/api/swirl/...`, both hitting the same views. Galaxy uses `/api/`; `curl` works with either.

### Release branches

`main_prerelease_X_Y_Z` is cut from main, merges develop once, then sits. When a regression is reported on a release branch, check if the fix is already on develop and merge develop forward. Do not cherry-pick unless there is no alternative; cherry-picks tend to re-introduce regressions. Flag any cherry-pick as "triage, not the cure".

### When the user reports a problem

Their report is data, not a hypothesis to question. Investigate: `logs/django.log`, celery worker logs, the served bundle (`static/galaxy/`), what is actually running (`.pyc` mtime, `git log`). "Are you sure?" / "Did you restart?" / "Try again" are anti-patterns.

### Tests and closing out

- After any coding session: review tests, update them, add new ones, run them all.
- Nothing is done until all tests pass. Tests must reflect the user's experience, not just that the code executes.
- Verify before claiming done: code edit -> `pytest` the affected tests; backend endpoint -> `curl` the live endpoint; UI change -> reinstall, hard-refresh, inspect; git op -> `git status` / `git diff origin/<branch>`.
- Verify UI changes in a browser before turning work over.

### Ops

- Never restart workers individually. `python swirl.py restart` kills the whole stack (Celery plus Daphne restart together). Do not restart mid-demo without an OK.

### Tone

No glazing, no unreasonable positivity. Push back when something is wrong. Always be seeking to delight the SWIRL user.

## Operating discipline

Before any multi-step action, state in one sentence each: starting repo/branch, ending repo/branch, what gets pushed where. If you cannot, stop and work it out first.

Force-pushes: auto-mode denies them. If work needs a force-push (rebase, history rewrite), ask for authorization before the rebase, not after.

## Local installation flow

```bash
git clone -b develop <repository-url> swirl-search
cd swirl-search
./install.sh
python swirl.py setup
./install-ui.sh -p
python swirl.py start
```

Do not run install commands automatically unless the user asks and the target is clearly local or disposable.

## Security and secrets

This repo holds sensitive operational assets. Treat it as sensitive by default.

- Never print real API keys, OAuth/OIDC client secrets, DB passwords, tokens, private keys, or full `.env` contents. Use placeholders: `<api-key>`, `<client-secret>`, `<tenant-id>`, `<docker-token>`, `<database-password>`.
- Do not read `.env` without approval; do not suggest committing `.env` or credential-bearing files.
- When generating reusable docs: remove personal names and emails, replace local absolute paths with generic ones.

Treat the following paths as sensitive — do not print values from them:

```text
.env
.env.*
*.pem
*.key
swirl_server/settings*.py    (may contain DB credentials or secret key)
Postman collections containing auth examples
```

## High-risk commands (never run automatically; explicit approval required)

```text
docker login / docker push / docker buildx build --push
pg_restore / psql DROP|TRUNCATE
```

Prefer dry-run or review-only workflows where available. For Docker image builds, they are handled via GitHub Actions workflows — do not push images manually.

## Repo areas

- `DevUtils/`: dev, support, test, data, and API helpers. Read a script before suggesting its use; classify it read-only / local-mutating / networked / credentialed; gate credentialed and network-indexing scripts behind approval.
- `swirl_server/`: Django project (settings, urls). `static/galaxy/`: the served Galaxy UI bundle.
- `SearchProviders/`: provider JSON definitions loaded via `python swirl_load.py`.
- `AIProviders/`: AI provider JSON definitions loaded via `python swirl_load.py`.
- `.github/workflows/`: CI/CD pipelines (unit-tests, QA suite, Docker build, db-dist, docs).

## CI/CD workflows

| Workflow | Trigger | What it does |
|---|---|---|
| `unit-tests.yml` | PR to `develop` | pytest unit tests |
| `test-build-pipeline.yml` | push to `main`/`develop` | unit-tests → db-dist → qa-suite → docker build+push |
| `docker-image.yml` | manual | Docker build+push only |
| `qa-suite.yml` | manual | QA behave suite against live Swirl |
| `db-dist.yml` | via pipeline | regenerates `db.sqlite3.dist` |

Docker image: `swirlai/swirl-search`. Built and pushed via GitHub Actions only — never manually.

## AI Providers, Search, RAG, and the SWIRL Assistant

Provider roles: `reader`, `query`, `connector`, `rag`. Provider config may include `api_key`, `model`, `config`, `tags`, `defaults`. Do not print provider keys. Assume one active default per role unless code says otherwise. When changing RAG, check token limits, model compatibility, source ordering, and fallback. Page Fetcher and Tika changes affect extraction and RAG quality; validate MIME allowlists. Treat provider activate/deactivate as a runtime behavior change.

The SWIRL Assistant (chat plus RAG over federated results) is in scope. Changes that touch assistant routes, prompt assembly, or RAG distribution strategy must be verified end-to-end.

## Recommended validation

For Python changes:

```bash
python -m compileall <path>
```

For pre-checkin:

```bash
./install-test.sh
./DevUtils/pre-checkin-tests.sh
```

These require test dependencies (`requirements-test.txt`) and a running local SWIRL instance. Confirm prerequisites before running.

## Pull request summary

Match the structure from `.github/pull_request_template.md`. For code changes, also include:

```md
## Summary
## Type of change
## Files changed
## Runtime impact
## Search/RAG/Assistant impact
## Secrets impact
## Testing and Validation
```

## Context handoff

Use the context handoff skill before compacting, ending a session, or switching tasks. Capture:

- Current goal and branch.
- Files changed or reviewed.
- Commands run.
- Local install/configuration status.
- SearchProvider, AI Provider, RAG, Tika, or Page Fetcher changes.
- Known blockers and next safe action.

Never include secret values in a handoff.

## .claude structure

- Agents: `.claude/agents/`
- Skills: `.claude/skills/<name>/SKILL.md` (must live here to be auto-discovered)
- Commands: `.claude/commands/`
