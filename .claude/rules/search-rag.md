# Search, RAG, and Provider Configuration Rule

Apply this rule when changing SearchProviders, AI Providers, Page Fetcher configuration, Tika, RAG settings, provider migration scripts, benchmark scripts, or provider JSON.

## Sensitive fields

Treat these as sensitive:

- `api_key`
- OAuth/OIDC client secrets
- Provider credentials
- Bearer tokens
- Diffbot tokens
- Microsoft Graph tokens

## Review dimensions

Check:

- Provider role: `reader`, `query`, `connector`, `rag`.
- Active/default provider behavior.
- Model identifier and token limit compatibility.
- Page Fetcher timeout/fallback changes.
- Tika endpoint and MIME whitelist.
- RAG distribution strategy.
- Whether generated provider JSON contains secrets.
- Whether provider changes affect public web search, enterprise search, or authenticated content.

## Output format

```md
## Provider/RAG change summary
## SearchProvider impact
## AI Provider impact
## Page Fetcher/Tika impact
## Auth/token impact
## Secret exposure risk
## Validation plan
## Rollback notes
```
