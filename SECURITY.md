# Security Policy

## Supported versions

Only the latest minor release on the default branch is currently supported.

## Reporting a vulnerability

Do not publish access tokens, personal data, or exploitable details in a public issue.
Contact the repository owner privately through GitHub Security Advisories. Until a private contact channel is configured, do not include secrets in reports.

## Secret handling

- Keep credentials in environment variables or a managed secret store.
- Never commit `.env`, access tokens, API keys, signing keys, or client data.
- Rotate any credential that may have been exposed.
- Redact authorization headers and query-string tokens from logs.
