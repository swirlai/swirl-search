# Security and Secrets Rule

Apply this rule when working with API keys, `.env`, OAuth/OIDC/MSAL configuration, Docker credentials, Postman collections, database credentials, or GitHub Actions secrets.

## Never do

- Never print real secrets, tokens, passwords, private keys, or API keys.
- Never copy values from `.env` or Postman collections into generated docs.
- Never replace placeholders with real secrets.
- Never suggest committing `.env`, private keys, or credential-bearing files.
- Never print GitHub Actions secret values from workflow output or logs.

## Placeholder policy

Use placeholders only:

```text
<api-key>
<client-secret>
<tenant-id>
<docker-token>
<database-password>
<private-key>
<github-pat>
```

## Sanitization policy

When generating reusable documentation:

- Remove personal names.
- Remove personal email addresses.
- Replace local absolute paths with generic paths.
- Keep script filenames when needed for technical accuracy.

## Review checklist

Before approving changes, check:

- Were any real secrets added?
- Were any credentials moved from environment storage into Git?
- Were auth redirect URIs, issuer URLs, or token settings changed?
- Were GitHub Actions secrets referenced in new or changed workflow steps?
- Were generated outputs included accidentally?
