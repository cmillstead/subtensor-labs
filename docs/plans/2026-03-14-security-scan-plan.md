# Security Scan Implementation Plan — 2026-03-14

**Total findings**: 19 (2 CRIT, 5 HIGH, 7 MED, 5 LOW)
**Vault doc**: `Subtensor Labs Security Scan 2026-03-14.md`

---

## Phase 1: CRIT Severity (2 findings)

> **Note**: SEC-CRIT-1 (auth) is planned for Story 4.1 (Epic 4). SEC-CRIT-2 (rate limiting) should be added as a prerequisite to any user-facing deployment. These are expected gaps for a Story 1.1 scaffold.

### Task 1.1 — Implement authentication [SEC-CRIT-1]
- **Story**: 4.1 (Auth system)
- **Files**: apps/web/src/lib/auth.ts, apps/engine/engine/api/middleware (new), apps/web/src/app/api/proxy/[...path]/route.ts
- **Action**: Implement NextAuth.js + JWT. Add auth middleware to engine. Add session check to proxy route.
- **Tests**: Unauthenticated requests to user-scoped endpoints return 401.

### Task 1.2 — Add rate limiting [SEC-CRIT-2]
- **Files**: apps/engine/engine/main.py, pyproject.toml (add slowapi)
- **Action**: Add `slowapi` rate limiting middleware. Configure per-endpoint limits. Add rate limiting to proxy.
- **Tests**: 100 req/s returns 429 after threshold.

---

## Phase 2: HIGH Severity (5 findings) — Fix before any user data is stored

### Task 2.1 — Strip sensitive headers in proxy [SEC-HIGH-1]
- **Files**: apps/web/src/app/api/proxy/[...path]/route.ts
- **Action**: Replace blanket header forwarding with explicit allowlist. Strip `Cookie`, `Authorization`, `X-Forwarded-*`.
- **Tests**: 2 tests — verify Cookie/Authorization not forwarded.

### Task 2.2 — Validate CORS origins in production [SEC-HIGH-2]
- **Files**: apps/engine/engine/core/config.py, apps/engine/engine/main.py
- **Action**: Add Settings validator rejecting `*` in `cors_origins` when `debug=False`. Replace `allow_headers=["*"]` with explicit list.
- **Tests**: 2 tests — ValueError on wildcard origin in prod, specific headers returned.

### Task 2.3 — Implement coldkey address encryption [SEC-HIGH-3]
- **Files**: apps/engine/engine/models/user_address.py, apps/engine/engine/core/crypto.py (new), pyproject.toml (add cryptography)
- **Action**: Implement Fernet encryption using `address_encryption_key`. Encrypt on write, decrypt on read.
- **Tests**: Insert UserAddress, verify raw DB column is ciphertext.

### Task 2.4 — Add security headers [SEC-HIGH-4]
- **Files**: apps/web/next.config.js
- **Action**: Add X-Frame-Options, X-Content-Type-Options, Referrer-Policy, CSP, HSTS headers.
- **Tests**: Verify all headers present in response.

### Task 2.5 — Remove manual CORS from CatchAllMiddleware [SEC-HIGH-5]
- **Files**: apps/engine/engine/main.py
- **Action**: Remove manual CORS logic from CatchAllMiddleware. Let CORSMiddleware handle all CORS. May need middleware reordering.
- **Tests**: Existing CORS-on-error tests updated.

---

## Phase 3: MED Severity (7 findings)

### Task 3.1 — Separate DB connection settings [SEC-MED-1]
- **Files**: apps/engine/engine/core/config.py, apps/engine/engine/core/database.py
- **Action**: Add `db_user`, `db_password`, `db_host`, `db_port`, `db_name` settings. Construct URL programmatically. Keep `database_url` as override.
- **Tests**: Verify password never appears in logs.

### Task 3.2 — Add URL credential redaction to logging [SEC-MED-2, SEC-MED-3]
- **Files**: apps/engine/engine/core/logging.py
- **Action**: Extend `_redact_addresses` to also redact emails, credential-bearing URLs, Stripe IDs. Recursively check nested dict/list.
- **Tests**: Log event with email, db_url, stripe_id. Verify all redacted.

### Task 3.3 — Normalize proxy paths [SEC-MED-4]
- **Files**: apps/web/src/app/api/proxy/[...path]/route.ts, apps/web/src/__tests__/proxy-route.test.ts
- **Action**: Normalize path before `isAllowed` check. Reject segments containing `..`.
- **Tests**: Path traversal attempts return 403.

### Task 3.4 — Add migration SQL comment [SEC-MED-5]
- **Files**: apps/engine/migrations/versions/001_initial_schema.py
- **Action**: Add comment documenting static table names.
- **Tests**: N/A — documentation only.

### Task 3.5 — Use `uv sync --frozen` in CI [SEC-MED-6]
- **Files**: .github/workflows/ci.yml
- **Action**: Add `--frozen` flag to all `uv sync` commands.
- **Tests**: CI fails if lock file out of date.

### Task 3.6 — Add .dockerignore [SEC-MED-7]
- **Files**: apps/engine/.dockerignore (new)
- **Action**: Exclude .env*, .git, __pycache__, .mypy_cache, .ruff_cache, .pytest_cache, tests/, .venv/.
- **Tests**: Build image, verify no secrets.

---

## Phase 4: LOW Severity (5 findings)

### Task 4.1 — Document deployment architecture [SEC-LOW-1]
- **Action**: Add deployment section to README noting reverse proxy requirement.

### Task 4.2 — Narrow Python dependency ranges [SEC-LOW-2]
- **Files**: apps/engine/pyproject.toml
- **Action**: Change `>=` to `~=` or bounded ranges.

### Task 4.3 — Add dependency audit to CI [SEC-LOW-4]
- **Files**: .github/workflows/ci.yml
- **Action**: Add `npm audit --audit-level=high` and `pip-audit` steps.

### Task 4.4 — Remove version from public health response [SEC-LOW-5]
- **Files**: apps/engine/engine/api/health.py
- **Action**: Gate version behind authentication or remove from response.

### Task 4.5 — Audit napi-postinstall periodically [SEC-LOW-3]
- **Action**: No code change. Periodic audit.
