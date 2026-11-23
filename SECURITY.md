# Security Policy

- Require service bearer authentication and a valid demo namespace for temporary uploads and downloads.
- Validate file extensions, signatures, decoded size, and path ownership before render.
- Require explicit human review approval in the render request.
- Temporary media and render outputs are TTL-limited and must not be treated as permanent storage.
- Do not commit `api_assets`, `api_renders`, client media, or service credentials.
