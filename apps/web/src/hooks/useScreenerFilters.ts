"use client";

import { useMemo, useState, useCallback } from "react";
import type { ScreenerFilter, ScreenerSubnet } from "@/types";

/** Basic filter fields — available to all users */
const BASIC_FILTER_MAP = [
  { min: "min_miners", max: "max_miners", data: "miner_count" },
  { min: "min_validators", max: "max_validators", data: "validator_count" },
  {
    min: "min_registration_cost",
    max: "max_registration_cost",
    data: "registration_cost",
  },
  {
    min: "min_emission_share",
    max: "max_emission_share",
    data: "emission_share",
  },
  { min: "min_alpha_price", max: "max_alpha_price", data: "alpha_price" },
  {
    min: "min_subnet_age_days",
    max: "max_subnet_age_days",
    data: "subnet_age_days",
  },
] as const;

/** Advanced filter fields — premium only */
const ADVANCED_FILTER_MAP = [
  {
    min: "min_alpha_price_change_24h",
    max: "max_alpha_price_change_24h",
    data: "alpha_price_change_24h",
  },
  {
    min: "min_alpha_price_change_7d",
    max: "max_alpha_price_change_7d",
    data: "alpha_price_change_7d",
  },
  {
    min: "min_alpha_price_change_30d",
    max: "max_alpha_price_change_30d",
    data: "alpha_price_change_30d",
  },
  {
    min: "min_alpha_market_cap",
    max: "max_alpha_market_cap",
    data: "alpha_market_cap",
  },
  {
    min: "min_net_tao_inflow",
    max: "max_net_tao_inflow",
    data: "net_tao_inflow",
  },
  { min: "min_fill_rate", max: "max_fill_rate", data: "fill_rate" },
  {
    min: "min_owner_take_rate",
    max: "max_owner_take_rate",
    data: "owner_take_rate",
  },
] as const;

/** Combined filter field map for all range filters */
const FILTER_FIELD_MAP = [...BASIC_FILTER_MAP, ...ADVANCED_FILTER_MAP] as const;

type FilterMinKey = (typeof FILTER_FIELD_MAP)[number]["min"];
type FilterMaxKey = (typeof FILTER_FIELD_MAP)[number]["max"];
type FilterKey = FilterMinKey | FilterMaxKey | "immunity_active";

export const EMPTY_FILTERS: ScreenerFilter = {
  // Basic
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
  // Advanced
  min_alpha_price_change_24h: null,
  max_alpha_price_change_24h: null,
  min_alpha_price_change_7d: null,
  max_alpha_price_change_7d: null,
  min_alpha_price_change_30d: null,
  max_alpha_price_change_30d: null,
  min_alpha_market_cap: null,
  max_alpha_market_cap: null,
  min_net_tao_inflow: null,
  max_net_tao_inflow: null,
  min_fill_rate: null,
  max_fill_rate: null,
  min_owner_take_rate: null,
  max_owner_take_rate: null,
  immunity_active: null,
  // Sort
  sort_by: "emission_share",
  sort_direction: "desc",
};

export function applyFilters(
  subnets: ScreenerSubnet[],
  filters: ScreenerFilter,
): ScreenerSubnet[] {
  return subnets.filter((subnet) => {
    // Range filters (basic + advanced)
    for (const { min, max, data } of FILTER_FIELD_MAP) {
      const minVal = filters[min];
      const maxVal = filters[max];
      if (minVal === null && maxVal === null) continue;

      const value = subnet[data as keyof ScreenerSubnet] as number | null;
      // Null data does not match any range filter
      if (value === null || value === undefined) return false;
      if (minVal !== null && value < minVal) return false;
      if (maxVal !== null && value > maxVal) return false;
    }

    // Boolean immunity filter
    if (filters.immunity_active !== null) {
      if (subnet.immunity_active !== filters.immunity_active) return false;
    }

    return true;
  });
}

export function getActiveFilterCount(filters: ScreenerFilter): number {
  let count = 0;
  for (const { min, max } of FILTER_FIELD_MAP) {
    if (filters[min] !== null || filters[max] !== null) {
      count++;
    }
  }
  // Count immunity filter
  if (filters.immunity_active !== null) count++;
  return count;
}

/** Count only basic (free tier) active filters */
export function getBasicFilterCount(filters: ScreenerFilter): number {
  let count = 0;
  for (const { min, max } of BASIC_FILTER_MAP) {
    if (filters[min] !== null || filters[max] !== null) {
      count++;
    }
  }
  return count;
}

/** Count only advanced (premium) active filters */
export function getAdvancedFilterCount(filters: ScreenerFilter): number {
  let count = 0;
  for (const { min, max } of ADVANCED_FILTER_MAP) {
    if (filters[min] !== null || filters[max] !== null) {
      count++;
    }
  }
  if (filters.immunity_active !== null) count++;
  return count;
}

export function useScreenerFilters(subnets: ScreenerSubnet[] | undefined) {
  const [filters, setFilters] = useState<ScreenerFilter>(EMPTY_FILTERS);

  const filteredSubnets = useMemo(() => {
    if (!subnets) return [];
    return applyFilters(subnets, filters);
  }, [subnets, filters]);

  const activeFilterCount = useMemo(
    () => getActiveFilterCount(filters),
    [filters],
  );

  const setFilter = useCallback(
    (key: FilterKey, value: number | boolean | null) => {
      setFilters((prev) => ({ ...prev, [key]: value }));
    },
    [],
  );

  const resetFilters = useCallback(() => {
    setFilters(EMPTY_FILTERS);
  }, []);

  return {
    filters,
    setFilters,
    filteredSubnets,
    activeFilterCount,
    setFilter,
    resetFilters,
  };
}
