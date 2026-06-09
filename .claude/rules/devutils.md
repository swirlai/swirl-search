# DevUtils Rule

Apply this rule when changing or using scripts under `DevUtils/`.

## Categories

- Test/check-in: `pre-checkin-tests.sh`, `run-integtration-tests.sh`.
- API/search verification: `verify_search.py`, `Swirl.postman_collection.json`.
- Repository utility: `clone_swirl.sh`.
- Data/indexing: `fix_csv.py`, `index_email_elastic.py`, `index_email_opensearch.py`.

## Rules

- Read the script before suggesting usage.
- Identify whether the script is read-only, local-mutating, networked, or credentialed.
- Do not run credentialed, external, or network-indexing scripts without approval.
- Do not print arguments that contain passwords, bearer tokens, or API keys.
- `clone_swirl.sh` prompts for a GitHub PAT interactively — do not pass the PAT on the command line.

## Output requirement

For any DevUtils script recommendation, provide:

```md
## Script
## Purpose
## Inputs required
## External systems touched
## Mutating behavior
## Secrets involved
## Safe dry-run/test option
## Recommended command
```
