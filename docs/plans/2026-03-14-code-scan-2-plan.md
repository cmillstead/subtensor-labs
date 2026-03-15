# Code Scan Remediation Plan — 2026-03-14 (Post-Epic 2)

**Findings**: 16 total (0 CRIT, 3 HIGH, 7 MED, 6 LOW)
**Vault doc**: `Subtensor Labs Code Scan 2026-03-14-2.md`

---

## Phase 1: HIGH (3 tasks, ~5 tests)

### Task 1: Fix delegation duplication bug in `_merge_positions` [CODE-HIGH-1]
- **Files**: `apps/engine/engine/portfolio/aggregator.py`
- **Fix**: Clear delegations from newly appended positions after merging into first position
- **Tests**: 1 — assert `merged[1].delegations` is empty after multi-hotkey merge

### Task 2: Align TS PortfolioResult with Python PortfolioResponseSchema [CODE-HIGH-2]
- **Files**: `packages/shared/types.ts`, `apps/web/src/types/index.ts`, all components consuming `PortfolioResult`
- **Fix**: Rename fields to match Python schema (`total_staked_tao`, `total_alpha_value_tao`), remove phantom fields
- **Tests**: 1 — contract test validating TS types against sample engine response
- **Note**: This is a breaking change across all frontend components. Update all references.

### Task 3: Rewrite usePortfolioHistory test [TEST-HIGH-1]
- **Files**: `apps/web/src/hooks/usePortfolioHistory.test.ts`
- **Fix**: Use `renderHook` + `QueryClientProvider` wrapper instead of direct fetch mock
- **Tests**: 3 — empty addresses disabled, successful response, error handling

---

## Phase 2: MED (7 tasks, ~10 tests)

### Task 4: Extract shared SS58 validation (Python) [CODE-MED-1]
- **Files**: `apps/engine/engine/schemas/__init__.py`, `portfolio.py`, `portfolio_history.py`
- **Tests**: 0 — existing schema tests cover

### Task 5: Extract shared SS58 validation (TypeScript) [CODE-MED-2]
- **Files**: `apps/web/src/lib/validation.ts` (new), `AddressManager.tsx`, `ExploreAddressInput.tsx`
- **Tests**: 1 — unit test for extracted helper

### Task 6: Use settings for history cache TTL [CODE-MED-3]
- **Files**: `apps/engine/engine/portfolio/history.py`
- **Tests**: 1 — verify history endpoint respects configured TTL

### Task 7: Parallelize coldkey resolution [CODE-MED-4]
- **Files**: `apps/engine/engine/portfolio/aggregator.py`
- **Tests**: 1 — multi-address benchmark

### Task 8: Deduplicate formatTaoShort in AllocationDonut [CODE-MED-5]
- **Files**: `apps/web/src/components/portfolio/AllocationDonut.tsx`
- **Tests**: 0 — existing tests cover

### Task 9: Add tests for proxy-allowlist, proxy route, engine-client, query-client [TEST-MED-1]
- **Files**: New test files for each module
- **Tests**: 4+ — path traversal, forwarding, error parsing, singleton

### Task 10: Add Dashboard page test [TEST-MED-2]
- **Files**: `apps/web/src/app/(auth)/dashboard/page.test.tsx` (new)
- **Tests**: 5+ — persistence, time range, CSV button, history chart, errors

---

## Phase 3: LOW (6 tasks, ~2 tests)

### Task 11: Add `total_value` computed field [CODE-LOW-1]
- **Files**: Types and components
- **Tests**: 0

### Task 12: Extract truncateAddress utility [CODE-LOW-2]
- **Files**: `apps/web/src/lib/utils.ts`, `AddressManager.tsx`, `SubnetPositionCard.tsx`
- **Tests**: 1

### Task 13: Replace MD5 with SHA256 for cache keys [CODE-LOW-3]
- **Files**: `apps/engine/engine/portfolio/history.py`
- **Tests**: 0

### Task 14: Extract test helper factories to conftest [CODE-LOW-4]
- **Files**: `apps/engine/tests/portfolio/conftest.py`
- **Tests**: 0

### Task 15: Move bittensor stub to conftest [TEST-LOW-1]
- **Files**: `apps/engine/tests/conftest.py`
- **Tests**: 0

### Task 16: Fix implicit afterEach import [TEST-LOW-2]
- **Files**: `apps/web/src/components/portfolio/PortfolioSummary.test.tsx`
- **Tests**: 0

---

## Summary

| Phase | Tasks | Tests to add | Effort |
|-------|-------|-------------|--------|
| Phase 1 (HIGH) | 3 | ~5 | 1-2 hours |
| Phase 2 (MED) | 7 | ~10 | 2-3 hours |
| Phase 3 (LOW) | 6 | ~2 | 1 hour |
| **Total** | **16** | **~17** | **4-6 hours** |
