# Code Review Summary

## Overview
AliceLM combines a FastAPI backend with a Next.js frontend to ingest Bilibili content, transcribe it, and expose conversational and RAG capabilities. The backend uses layered YAML + environment configuration, SQLAlchemy models, and bcrypt-based authentication. Below are notable observations from a quick security and reliability pass.

## Strengths
- Clear configuration layering with environment overrides, and sensible defaults for provider selection.
- Authentication routes consistently use FastAPI dependency injection and bcrypt hashing.
- Data models capture multi-tenant boundaries (tenant_id on core tables) and keep referential constraints explicit.

## Key Risks & Recommendations
1. **Default secret key is hard-coded** – `Settings.secret_key` ships as "change-me-in-production", which risks weak JWT signing in misconfigured deployments. Promote a required environment variable or enforce a startup check that rejects the placeholder value before issuing tokens.
2. **Passwordless login in debug mode** – `AuthService.authenticate` bypasses password verification when `debug` is enabled and the stored hash is empty. If `ALICE_DEBUG` is accidentally enabled in shared environments this yields account takeover. Restrict the shortcut to explicit test fixtures (e.g., feature flag + test-only environment) or remove it entirely.
3. **Credential storage in plaintext** – `UserPlatformBinding.credentials` stores third-party tokens as opaque text. Encrypt at rest (e.g., Fernet with envelope encryption) and/or restrict fields to scoped, expiring tokens; add secrets rotation and auditing.
4. **JWT token model lacks revocation/rotation** – Tokens are long-lived (24h) with a single HS256 secret and no audience/issuer claims. Add refresh/rotation, issuer/audience validation, and a revocation list or short-lived access tokens plus refresh tokens to limit blast radius on leak.
5. **Secrets validation on startup** – Given the number of external providers, add a startup check that validates required keys (LLM, RAG, Bilibili) per provider to fail fast instead of encountering runtime errors in workers.

## Suggested Next Steps
- Add a configuration validator that rejects default/empty secrets and ensures provider-specific keys are present.
- Gate the debug password bypass behind a dedicated `ALLOW_DEV_PASSWORDLESS_LOGIN` flag scoped to non-production environments.
- Encrypt `UserPlatformBinding.credentials`, and document rotation/expiry expectations for upstream tokens.
- Introduce short-lived access tokens with refresh tokens, plus optional token revocation for admin-driven logout.
- Expand automated tests around auth edge cases (invalid token, expired token, password change) and credential handling.
