import { describe, it, expect } from "vitest";
import { renderHook, act } from "@testing-library/react";
import {
  applyFilters,
  getActiveFilterCount,
  useScreenerFilters,
} from "./useScreenerFilters";
import type { ScreenerFilter, ScreenerSubnet } from "@/types";

const EMPTY_FILTERS: ScreenerFilter = {
  min_miners: null,
  max_miners: null,
  min_validators: null,
  max_validators: null,
  min_registration_cost: null,
  max_registration_cost: null,
  min_emission_share: null,
  max_emission_share: null,
  min_alpha_price: null,
  max_alpha_price: null,
  min_subnet_age_days: null,
  max_subnet_age_days: null,
  sort_by: "emission_share",
  sort_direction: "desc",
};

function makeSubnet(overrides: Partial<ScreenerSubnet> = {}): ScreenerSubnet {
  return {
    netuid: 1,
    name: "Test Subnet",
    miner_count: 100,
    validator_count: 50,
    registration_cost: 1.5,
    emission_share: 0.05,
    alpha_price: 0.12,
    alpha_market_cap: 1200,
    fill_rate: 0.78,
    owner_take_rate: 0.18,
    tao_reserves: 500,
    alpha_reserves: 4000,
    subnet_age_days: 120,
    sparkline_emission_7d: [0.04, 0.05],
    sparkline_price_7d: [0.10, 0.12],
    ...overrides,
  };
}

const SUBNETS: ScreenerSubnet[] = [
  makeSubnet({ netuid: 1, miner_count: 100, validator_count: 50, registration_cost: 1.5, emission_share: 0.05, alpha_price: 0.12, subnet_age_days: 120 }),
  makeSubnet({ netuid: 2, miner_count: 200, validator_count: 30, registration_cost: 3.0, emission_share: 0.10, alpha_price: 0.25, subnet_age_days: 60 }),
  makeSubnet({ netuid: 3, miner_count: 50, validator_count: 80, registration_cost: 0.5, emission_share: 0.02, alpha_price: 0.08, subnet_age_days: 200 }),
];

describe("applyFilters", () => {
  it("returns all subnets when no filters set", () => {
    const result = applyFilters(SUBNETS, EMPTY_FILTERS);
    expect(result).toHaveLength(3);
  });

  it("filters by single criterion — min_miners", () => {
    const filters = { ...EMPTY_FILTERS, min_miners: 80 };
    const result = applyFilters(SUBNETS, filters);
    expect(result).toHaveLength(2);
    expect(result.map((s) => s.netuid)).toEqual([1, 2]);
  });

  it("filters by single criterion — max_miners", () => {
    const filters = { ...EMPTY_FILTERS, max_miners: 100 };
    const result = applyFilters(SUBNETS, filters);
    expect(result).toHaveLength(2);
    expect(result.map((s) => s.netuid)).toEqual([1, 3]);
  });

  it("filters by min and max range", () => {
    const filters = { ...EMPTY_FILTERS, min_miners: 80, max_miners: 150 };
    const result = applyFilters(SUBNETS, filters);
    expect(result).toHaveLength(1);
    expect(result[0].netuid).toBe(1);
  });

  it("applies AND logic across multiple criteria", () => {
    const filters = {
      ...EMPTY_FILTERS,
      min_miners: 80,
      min_emission_share: 0.04,
    };
    const result = applyFilters(SUBNETS, filters);
    expect(result).toHaveLength(2);
    expect(result.map((s) => s.netuid)).toEqual([1, 2]);
  });

  it("applies AND logic that narrows to single result", () => {
    const filters = {
      ...EMPTY_FILTERS,
      min_miners: 150,
      min_emission_share: 0.08,
    };
    const result = applyFilters(SUBNETS, filters);
    expect(result).toHaveLength(1);
    expect(result[0].netuid).toBe(2);
  });

  it("returns empty array when no subnets match", () => {
    const filters = { ...EMPTY_FILTERS, min_miners: 300 };
    const result = applyFilters(SUBNETS, filters);
    expect(result).toHaveLength(0);
  });

  it("handles min only (no max)", () => {
    const filters = { ...EMPTY_FILTERS, min_subnet_age_days: 100 };
    const result = applyFilters(SUBNETS, filters);
    expect(result).toHaveLength(2);
    expect(result.map((s) => s.netuid)).toEqual([1, 3]);
  });

  it("handles max only (no min)", () => {
    const filters = { ...EMPTY_FILTERS, max_registration_cost: 1.5 };
    const result = applyFilters(SUBNETS, filters);
    expect(result).toHaveLength(2);
    expect(result.map((s) => s.netuid)).toEqual([1, 3]);
  });

  it("uses inclusive range checks", () => {
    const filters = { ...EMPTY_FILTERS, min_miners: 100, max_miners: 100 };
    const result = applyFilters(SUBNETS, filters);
    expect(result).toHaveLength(1);
    expect(result[0].netuid).toBe(1);
  });

  it("handles empty subnet array", () => {
    const result = applyFilters([], { ...EMPTY_FILTERS, min_miners: 1 });
    expect(result).toHaveLength(0);
  });
});

describe("getActiveFilterCount", () => {
  it("returns 0 when no filters are active", () => {
    expect(getActiveFilterCount(EMPTY_FILTERS)).toBe(0);
  });

  it("counts a filter with only min set as 1", () => {
    expect(
      getActiveFilterCount({ ...EMPTY_FILTERS, min_miners: 50 }),
    ).toBe(1);
  });

  it("counts a filter with only max set as 1", () => {
    expect(
      getActiveFilterCount({ ...EMPTY_FILTERS, max_miners: 200 }),
    ).toBe(1);
  });

  it("counts a filter with both min and max as 1", () => {
    expect(
      getActiveFilterCount({
        ...EMPTY_FILTERS,
        min_miners: 50,
        max_miners: 200,
      }),
    ).toBe(1);
  });

  it("counts multiple active filters", () => {
    expect(
      getActiveFilterCount({
        ...EMPTY_FILTERS,
        min_miners: 50,
        max_emission_share: 0.1,
        min_subnet_age_days: 30,
      }),
    ).toBe(3);
  });

  it("counts all 6 filter categories", () => {
    expect(
      getActiveFilterCount({
        ...EMPTY_FILTERS,
        min_miners: 1,
        min_validators: 1,
        min_registration_cost: 0,
        min_emission_share: 0,
        min_alpha_price: 0,
        min_subnet_age_days: 0,
      }),
    ).toBe(6);
  });
});

describe("useScreenerFilters", () => {
  it("returns empty filtered subnets when data is undefined", () => {
    const { result } = renderHook(() => useScreenerFilters(undefined));
    expect(result.current.filteredSubnets).toEqual([]);
    expect(result.current.activeFilterCount).toBe(0);
  });

  it("returns all subnets when no filters active", () => {
    const { result } = renderHook(() => useScreenerFilters(SUBNETS));
    expect(result.current.filteredSubnets).toHaveLength(3);
    expect(result.current.activeFilterCount).toBe(0);
  });

  it("filters subnets when setFilter is called", () => {
    const { result } = renderHook(() => useScreenerFilters(SUBNETS));

    act(() => {
      result.current.setFilter("min_miners", 80);
    });

    expect(result.current.filteredSubnets).toHaveLength(2);
    expect(result.current.activeFilterCount).toBe(1);
  });

  it("resetFilters clears all filter state", () => {
    const { result } = renderHook(() => useScreenerFilters(SUBNETS));

    act(() => {
      result.current.setFilter("min_miners", 80);
      result.current.setFilter("max_emission_share", 0.06);
    });

    expect(result.current.activeFilterCount).toBe(2);

    act(() => {
      result.current.resetFilters();
    });

    expect(result.current.filteredSubnets).toHaveLength(3);
    expect(result.current.activeFilterCount).toBe(0);
  });
});
