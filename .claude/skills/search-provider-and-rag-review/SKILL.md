---
name: search-provider-and-rag-review
description: Use this skill when changing SearchProvider, AI Provider, Page Fetcher, Tika, or RAG configuration.
---

# Search Provider and RAG Review Skill

## Objective

Review search, provider, and RAG configuration safely.

## Process

1. Identify whether the change affects SearchProviders, AI Providers, Page Fetcher, Tika, or RAG.
2. Identify provider roles and active/default behavior.
3. Identify secrets in provider JSON/configuration.
4. Check model and token configuration.
5. Check page fetching timeout/fallback behavior.
6. Check Tika endpoint and MIME whitelist.
7. Define validation searches or API calls.

## Output format

```md
## Change summary
## SearchProvider impact
## AI Provider impact
## RAG behavior impact
## Page Fetcher/Tika impact
## Secrets involved
## Validation plan
## Rollback notes
```

## Rules

- Do not expose provider API keys.
- Do not generate real provider secrets.
- Use sanitized sample JSON only.
