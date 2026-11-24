# Security Policy

- Never commit `.env`, service keys, uploaded media, render outputs, user content or private deployment configuration.
- Deploy the render API only behind HTTPS and trusted server-side authorization.
- The service bearer key is a service credential, not a user session.
- The demo ID is a namespace separator, not a replacement for account authentication.
- Keep user-to-project authorization, approval audit records, quotas and billing enforcement in the VYRO backend.
- Apply body-size limits, malware scanning, retention policy and storage access controls at deployment.
- Report vulnerabilities privately to the repository maintainer; do not disclose secrets or exploit details in public issues.
