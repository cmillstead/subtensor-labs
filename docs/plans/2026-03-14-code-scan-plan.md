# Code Scan Implementation Plan — 2026-03-14

**Total tasks**: 18 findings (0 CRIT, 5 HIGH, 8 MED, 4 LOW)
**Total tests to add**: ~30+ new test cases across Python and TypeScript
**Vault doc**: `Subtensor Labs Code Scan 2026-03-14.md`

---

## Phase 1: HIGH Severity (5 findings)

### Task 1.1 — Set up Vitest for TypeScript testing [TEST-HIGH-1]
- **Files**: apps/web/package.json, apps/web/vitest.config.ts (new), apps/web/src/**/*.test.ts (new)
- **Action**: Install Vitest + React Testing Library. Create config. Write initial tests for:
  - `isAllowed()` path validation in proxy route (security boundary)
  - `engineFetch` success/error paths
  - `CACHE_TTL` and `RAO_PER_TAO` constant values
- **Tests**: ~8 new test cases
- **Depends on**: CODE-HIGH-1, CODE-HIGH-2 (fix duplication first, then test)

### Task 1.2 — Fix ENGINE_URL duplication [CODE-HIGH-1]
- **Files**: apps/web/src/app/api/proxy/[...path]/route.ts
- **Action**: Replace inline `ENGINE_URL` with import from `../../../lib/constants`
- **Tests**: 1 test confirming import source

### Task 1.3 — Deduplicate proxy route handlers [CODE-HIGH-2]
- **Files**: apps/web/src/app/api/proxy/[...path]/route.ts
- **Action**: Create `makeHandler()` factory, export GET/POST/PUT/DELETE from it
- **Tests**: 4 tests (one per HTTP method) via Vitest

### Task 1.4 — Add async safety to singleton initialization [CODE-HIGH-3]
- **Files**: apps/engine/engine/core/database.py, apps/engine/engine/core/redis.py
- **Action**: Add `asyncio.Lock` to `get_engine()` and `get_redis()` lazy init
- **Tests**: 3 tests — singleton identity, dispose-then-reinit, concurrent access

### Task 1.5 — Resolve or document dead `engineFetch` [CODE-HIGH-4]
- **Files**: apps/web/src/lib/engine-client.ts
- **Action**: Add JSDoc explaining intended usage (server components vs proxy for browser)
- **Tests**: Deferred until `engineFetch` is wired up in a story

### Task 1.6 — Add ORM model tests [TEST-HIGH-2]
- **Files**: apps/engine/tests/models/ (new directory + test files)
- **Action**: Create tests for all 10 models — instantiation, composite PKs, FK constraints
- **Tests**: ~10 new test cases

### Task 1.7 — Add DB/Redis lifecycle tests [TEST-HIGH-3]
- **Files**: apps/engine/tests/core/ (new directory + test files)
- **Action**: Test get_engine singleton, dispose, get_session, cache ops, health check failure paths
- **Tests**: ~8 new test cases

---

## Phase 2: MED Severity (8 findings)

### Task 2.1 — Health endpoint returns 503 when degraded [CODE-MED-5]
- **Files**: apps/engine/engine/api/health.py, apps/engine/tests/api/test_health.py
- **Action**: Return 503 when status is "degraded"
- **Tests**: Update existing test assertions from 200 to 503

### Task 2.2 — Wire up BaseSchema for all schemas [CODE-MED-6]
- **Files**: apps/engine/engine/schemas/*.py, apps/engine/engine/api/health.py
- **Action**: Change all schema classes to extend `BaseSchema`
- **Tests**: 1 parametrized test asserting `issubclass(cls, BaseSchema)`

### Task 2.3 — Add CORS headers to CatchAllMiddleware errors [CODE-MED-8]
- **Files**: apps/engine/engine/main.py
- **Action**: Add `Access-Control-Allow-Origin` to error responses in CatchAllMiddleware
- **Tests**: 1 test asserting CORS header on 500 response

### Task 2.4 — Add ORM relationships [CODE-MED-9]
- **Files**: apps/engine/engine/models/user.py, user_address.py, alert_config.py, alert_history.py, saved_screener.py
- **Action**: Add `relationship()` with appropriate `cascade` settings
- **Tests**: 2 tests — cascade delete, relationship navigation

### Task 2.5 — Add cross-reference comments for shared constants [CODE-MED-10]
- **Files**: apps/engine/engine/core/config.py, packages/shared/constants.ts
- **Action**: Add comments noting manual synchronization requirement
- **Tests**: N/A (documentation only)

### Task 2.6 — Make `setup_logging()` respect debug flag [CODE-MED-11]
- **Files**: apps/engine/engine/core/logging.py
- **Action**: Switch to `ConsoleRenderer` when `debug=True`
- **Tests**: 2 tests — debug=True uses console, debug=False uses JSON

### Task 2.7 — Add Settings validation tests [TEST-MED-4]
- **Files**: apps/engine/tests/core/test_config.py (new)
- **Action**: Test `validate_encryption_key` behavior
- **Tests**: 3 test cases

### Task 2.8 — Fix test fixture global app mutation [TEST-MED-6]
- **Files**: apps/engine/tests/api/test_error_handlers.py
- **Action**: Add fixture teardown to clean up test routes
- **Tests**: Verify existing tests still pass after cleanup

---

## Phase 3: LOW Severity (4 findings)

### Task 3.1 — Move ENGINE_VERSION to canonical location [CODE-LOW-12]
- **Files**: apps/engine/engine/__init__.py, apps/engine/engine/schemas/errors.py, apps/engine/engine/main.py
- **Action**: Use `importlib.metadata.version()` or `__version__` in `__init__.py`
- **Tests**: 1 test asserting version matches pyproject.toml

### Task 3.2 — Add explanation to type: ignore comments [CODE-LOW-14]
- **Files**: apps/engine/engine/core/redis.py
- **Action**: Add reason string to `# type: ignore` comment
- **Tests**: N/A

### Task 3.3 — Add real-service health check tests [TEST-LOW-7]
- **Files**: apps/engine/tests/core/test_health_checks.py (new)
- **Action**: Test `check_db_health()` and `check_redis_health()` against CI services
- **Tests**: 2 test cases

### Task 3.4 — Migration integration tests [TEST-MED-5]
- **Files**: apps/engine/tests/integration/test_migration.py (new)
- **Action**: Test upgrade/downgrade, verify hypertables and compression
- **Tests**: 3 test cases
