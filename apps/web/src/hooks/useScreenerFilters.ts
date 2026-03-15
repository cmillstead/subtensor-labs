"use client";

import { useMemo, useState, useCallback } from "react";
import type { ScreenerFilter, ScreenerSubnet } from "@/types";

const FILTER_FIELD_MAP = [
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

type FilterMinKey = (typeof FILTER_FIELD_MAP)[number]["min"];
type FilterMaxKey = (typeof FILTER_FIELD_MAP)[number]["max"];
type FilterKey = FilterMinKey | FilterMaxKey;

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

export function applyFilters(
  subnets: ScreenerSubnet[],
  filters: ScreenerFilter,
): ScreenerSubnet[] {
  return subnets.filter((subnet) =>
    FILTER_FIELD_MAP.every(({ min, max, data }) => {
      const minVal = filters[min];
      const maxVal = filters[max];
      if (minVal === null && maxVal === null) return true;
      const value = subnet[data];
      if (minVal !== null && value < minVal) return false;
      if (maxVal !== null && value > maxVal) return false;
      return true;
    }),
  );
}

export function getActiveFilterCount(filters: ScreenerFilter): number {
  let count = 0;
  for (const { min, max } of FILTER_FIELD_MAP) {
    if (filters[min] !== null || filters[max] !== null) {
      count++;
    }
  }
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
    (key: FilterKey, value: number | null) => {
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
