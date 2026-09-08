# Deployment and CI/CD Rule

Apply this rule when working with GitHub Actions workflows (`.github/workflows/`), Docker build scripts, or any push/publish operation.

## High-risk areas

- Docker image build and push to Docker Hub.
- GitHub Actions workflow changes that trigger on push to `main` or `develop`.
- Secrets referenced in workflows (`SBS_DOCKER_USER`, `SBS_DOCKER_PAT`, `QA_*` secrets).
- `db.sqlite3.dist` auto-update pipeline (modifies committed file via PR).

## Rules

- Do not push Docker images manually — all builds go through GitHub Actions.
- Do not trigger `workflow_dispatch` workflows without explicit approval when they push images.
- Do not print or log GitHub Actions secret values.
- Review workflow trigger paths before proposing changes to `paths-ignore` filters.
- Treat the QA suite secrets (OpenSearch/Elasticsearch credentials, API keys) as sensitive.

## Required review output

```md
## Workflow/script involved
## Trigger and conditions
## Secrets used
## Artifacts affected (images, db files, docs)
## Push/publish behavior
## Commands proposed
## Approval required
## Rollback notes
```
