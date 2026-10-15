---
name: local-install-plan
description: Use this skill before installing, configuring, or troubleshooting a local SWIRL community environment.
---

# Local Install Plan Skill

## Objective

Create a safe, reviewable local installation or troubleshooting plan for SWIRL community edition.

## Installation flow

```bash
git clone -b develop <repository-url> swirl-search
cd swirl-search
./install.sh              # pip install, spacy model, NLTK
python swirl.py setup     # migrations, initial admin, collectstatic
./install-ui.sh -p        # pull swirlai/spyglass:preview, copy to static/galaxy/
python swirl.py start     # start Daphne + Celery
```

## Process

1. Confirm platform is supported (Linux/macOS, Python 3.11+).
2. Confirm Python, Redis, disk, and memory prerequisites.
3. Identify whether this is a fresh install, upgrade, or repair.
4. Check whether `.env` exists without printing it.
5. Plan DB setup steps (`python swirl.py setup`).
6. Plan UI install steps (`./install-ui.sh -p` or `--directory` for local build).
7. Plan startup and validation.

## Output format

```md
## Install goal
## Prerequisites
## Files/configuration involved
## Secrets handling
## Commands to run
## Validation
## Risks
## Rollback/cleanup
```

## Rules

- Do not print `.env` values.
- Do not run install/start commands unless explicitly approved.
- Mark local/disposable environment vs any external system clearly.
- `./install-ui.sh` requires Docker to be running unless using `-d <local-dir>`.
