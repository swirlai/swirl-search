---
name: docker-image-build-plan
description: Use this skill when reviewing or discussing Docker image builds, GitHub Actions Docker workflows, or Docker Hub publishing for swirl-search.
---

# Docker Image Build Plan Skill

## Objective

Review Docker image build and publish workflows safely. In this repo, all Docker builds and pushes happen through GitHub Actions — never manually.

## Build mechanism

Docker images are built via `.github/workflows/`:

- `docker-image.yml` — manual workflow, builds and pushes `swirlai/swirl-search:<tag>`.
- `test-build-pipeline.yml` — automated pipeline (push to `main`/`develop`); unit-tests → db-dist → qa-suite → docker build+push.

The `Dockerfile` at the root builds a multi-arch (`linux/amd64,linux/arm64`) image. The tag is `latest` on `main` and the branch name on other branches.

## Process

1. Identify whether a manual or automated build is needed.
2. Confirm branch and the resulting image tag.
3. Confirm Docker Hub secrets (`SBS_DOCKER_USER`, `SBS_DOCKER_PAT`) are in place — do not print them.
4. Confirm SBOM and provenance attestation requirements.
5. Identify any Dockerfile changes and validate locally with `docker build` (no `--push`).
6. Document produced tags.

## Output format

```md
## Image build summary
## Workflow used
## Branch/tag
## Build platform
## Push behavior
## Secrets involved
## Local validation command (no --push)
## Approval required
## Risks
```

## Rules

- Do not run `docker login` or `docker push` outside GitHub Actions without explicit approval.
- Do not print Docker Hub credentials.
- Local test builds must omit `--push`.
