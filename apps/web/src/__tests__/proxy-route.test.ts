import { describe, it, expect } from "vitest";
import { isAllowed, ALLOWED_PREFIXES } from "@/lib/proxy-allowlist";

describe("isAllowed", () => {
  it("allows all declared prefix paths", () => {
    for (const prefix of ALLOWED_PREFIXES) {
      expect(isAllowed(prefix)).toBe(true);
    }
  });

  it("allows paths with additional segments under a prefix", () => {
    expect(isAllowed("/engine/health/ready")).toBe(true);
    expect(isAllowed("/engine/portfolio/123/positions")).toBe(true);
    expect(isAllowed("/engine/screener/filters")).toBe(true);
  });

  it("rejects paths not in the allowlist", () => {
    expect(isAllowed("/engine/admin")).toBe(false);
    expect(isAllowed("/engine/users")).toBe(false);
    expect(isAllowed("/engine/internal")).toBe(false);
    expect(isAllowed("/")).toBe(false);
    expect(isAllowed("")).toBe(false);
  });

  it("rejects path traversal via .. segments", () => {
    // Path normalization resolves "../admin" so it no longer starts with /engine/health
    expect(isAllowed("/engine/health/../admin")).toBe(false);
    expect(isAllowed("/engine/health/../../etc/passwd")).toBe(false);
    expect(isAllowed("/engine/portfolio/../admin/secrets")).toBe(false);
  });

  it("rejects double-encoded traversal attempts", () => {
    // URL constructor normalizes these
    expect(isAllowed("/engine/health/%2e%2e/admin")).toBe(false);
  });

  it("rejects partial prefix matches", () => {
    expect(isAllowed("/engine/healthz")).toBe(true); // starts with /engine/health
    expect(isAllowed("/engine/scr")).toBe(false);
    expect(isAllowed("/engine/predict")).toBe(false);
  });
});
