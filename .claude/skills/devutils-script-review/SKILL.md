---
name: devutils-script-review
description: Use this skill to review, document, or propose safe execution of scripts under DevUtils/.
---

# DevUtils Script Review Skill

## Objective

Classify a DevUtils script before use and produce a safe execution recommendation.

## Known scripts

| Script | Risk level | Notes |
|---|---|---|
| `pre-checkin-tests.sh` | local | runs pytest + smoke tests |
| `run-integtration-tests.sh` | local + networked | requires live Swirl instance |
| `verify_search.py` | networked | POSTs to a search URL; requires credentials |
| `clone_swirl.sh` | credentialed | prompts for GitHub PAT interactively |
| `fix_csv.py` | local-mutating | modifies local CSV files |
| `index_email_elastic.py` | networked + credentialed | indexes into Elasticsearch |
| `index_email_opensearch.py` | networked + credentialed | indexes into OpenSearch |
| `Swirl.postman_collection.json` | read-only | may contain auth token examples |

## Process

1. Read the script.
2. Identify inputs, flags, defaults, and outputs.
3. Identify whether it touches local files, external APIs, search indexes, or auth systems.
4. Identify secrets or credentials involved.
5. Identify dry-run or read-only options.
6. Recommend a safe command or state that manual approval is required.

## Output format

```md
## Script
## Purpose
## Inputs/flags
## External systems touched
## Mutating behavior
## Secrets involved
## Safe execution mode
## Recommended command
## Approval required
```

## Rules

- Do not run credentialed or mutating scripts without approval.
- Do not print secrets.
- Prefer dry-run options when available.
