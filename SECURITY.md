# Security

## Public repository rules

- Never commit API keys, OAuth client secrets, refresh tokens, private keys or
  service-account files.
- Store runtime credentials only in GitHub Actions Secrets or another approved
  secret manager.
- Do not include credential values in issues, pull requests, logs or test
  fixtures.
- If a credential is suspected to be exposed, revoke or rotate it immediately
  and then investigate the repository history.

## Reporting

Do not open a public issue containing a secret or personal data. Use GitHub's
private vulnerability reporting channel for this repository when available.
