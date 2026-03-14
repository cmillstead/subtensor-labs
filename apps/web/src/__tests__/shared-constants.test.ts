import { describe, it, expect } from "vitest";
import {
  RAO_PER_TAO,
  EMISSION_PER_BLOCK,
  BLOCKS_PER_DAY,
  TAO_PER_DAY,
  CACHE_TTL,
} from "@subtensor-labs/shared";

describe("shared constants", () => {
  it("RAO_PER_TAO is 10^9", () => {
    expect(RAO_PER_TAO).toBe(1_000_000_000);
  });

  it("TAO_PER_DAY is derived correctly from emission and block rate", () => {
    expect(TAO_PER_DAY).toBe(EMISSION_PER_BLOCK * BLOCKS_PER_DAY);
  });

  it("CACHE_TTL values are positive integers", () => {
    for (const [key, value] of Object.entries(CACHE_TTL)) {
      expect(value, `CACHE_TTL.${key}`).toBeGreaterThan(0);
      expect(Number.isInteger(value), `CACHE_TTL.${key} is integer`).toBe(true);
    }
  });
});
