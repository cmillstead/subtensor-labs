"use client";

import { useMemo, useState } from "react";
import { useSession } from "next-auth/react";
import type { ScreenerFilter, ScreenerSubnet } from "@/types";
import { RangeInput } from "./RangeInput";
import { SavedScreenerPanel } from "./SavedScreenerPanel";
import { Button } from "@/components/ui/button";
import { PremiumGate } from "@/components/common/PremiumGate";
import { PremiumBadge } from "@/components/common/PremiumBadge";

interface FilterPanelProps {
  filters: ScreenerFilter;
  onFilterChange: (filters: ScreenerFilter) => void;
  onReset: () => void;
  activeFilterCount: number;
  subnetData: ScreenerSubnet[] | undefined;
}

interface FilterConfig {
  label: string;
  minKey: keyof ScreenerFilter;
  maxKey: keyof ScreenerFilter;
  dataField: keyof ScreenerSubnet;
  suffix?: string;
  step: number;
  displayScale?: number;
}

const BASIC_FILTER_CONFIGS: FilterConfig[] = [
  {
    label: "Miner Count",
    minKey: "min_miners",
    maxKey: "max_miners",
    dataField: "miner_count",
    step: 1,
  },
  {
    label: "Validator Count",
    minKey: "min_validators",
    maxKey: "max_validators",
    dataField: "validator_count",
    step: 1,
  },
  {
    label: "Registration Cost",
    minKey: "min_registration_cost",
    maxKey: "max_registration_cost",
    dataField: "registration_cost",
    suffix: "\u03C4",
    step: 0.01,
  },
  {
    label: "Emission Share",
    minKey: "min_emission_share",
    maxKey: "max_emission_share",
    dataField: "emission_share",
    suffix: "%",
    step: 0.01,
    displayScale: 100,
  },
  {
    label: "Alpha Price",
    minKey: "min_alpha_price",
    maxKey: "max_alpha_price",
    dataField: "alpha_price",
    suffix: "\u03C4",
    step: 0.0001,
  },
  {
    label: "Subnet Age",
    minKey: "min_subnet_age_days",
    maxKey: "max_subnet_age_days",
    dataField: "subnet_age_days",
    suffix: "days",
    step: 1,
  },
];

const ADVANCED_FILTER_CONFIGS: FilterConfig[] = [
  {
    label: "Price Change 24h",
    minKey: "min_alpha_price_change_24h",
    maxKey: "max_alpha_price_change_24h",
    dataField: "alpha_price_change_24h",
    suffix: "%",
    step: 0.1,
  },
  {
    label: "Price Change 7d",
    minKey: "min_alpha_price_change_7d",
    maxKey: "max_alpha_price_change_7d",
    dataField: "alpha_price_change_7d",
    suffix: "%",
    step: 0.1,
  },
  {
    label: "Price Change 30d",
    minKey: "min_alpha_price_change_30d",
    maxKey: "max_alpha_price_change_30d",
    dataField: "alpha_price_change_30d",
    suffix: "%",
    step: 0.1,
  },
  {
    label: "Alpha Market Cap",
    minKey: "min_alpha_market_cap",
    maxKey: "max_alpha_market_cap",
    dataField: "alpha_market_cap",
    suffix: "\u03C4",
    step: 0.01,
  },
  {
    label: "Net TAO Inflow",
    minKey: "min_net_tao_inflow",
    maxKey: "max_net_tao_inflow",
    dataField: "net_tao_inflow",
    suffix: "\u03C4",
    step: 0.1,
  },
  {
    label: "Fill Rate",
    minKey: "min_fill_rate",
    maxKey: "max_fill_rate",
    dataField: "fill_rate",
    suffix: "%",
    step: 1,
    displayScale: 100,
  },
  {
    label: "Owner Take Rate",
    minKey: "min_owner_take_rate",
    maxKey: "max_owner_take_rate",
    dataField: "owner_take_rate",
    suffix: "%",
    step: 1,
    displayScale: 100,
  },
];

const ALL_FILTER_CONFIGS = [...BASIC_FILTER_CONFIGS, ...ADVANCED_FILTER_CONFIGS];

function computeDataRange(
  subnets: ScreenerSubnet[] | undefined,
  field: keyof ScreenerSubnet,
  displayScale: number,
): { min: string; max: string } {
  if (!subnets || subnets.length === 0) return { min: "Min", max: "Max" };
  const values = subnets
    .map((s) => s[field] as number | null)
    .filter((v): v is number => v !== null);
  if (values.length === 0) return { min: "Min", max: "Max" };
  const min = Math.min(...values) * displayScale;
  const max = Math.max(...values) * displayScale;
  return {
    min: displayScale === 1 ? String(min) : min.toFixed(2),
    max: displayScale === 1 ? String(max) : max.toFixed(2),
  };
}

function toDisplayValue(
  value: number | null,
  displayScale: number,
): number | null {
  if (value === null) return null;
  return value * displayScale;
}

function fromDisplayValue(
  value: number | null,
  displayScale: number,
): number | null {
  if (value === null) return null;
  return value / displayScale;
}

export function FilterPanel({
  filters,
  onFilterChange,
  onReset,
  activeFilterCount,
  subnetData,
}: FilterPanelProps) {
  const [isOpen, setIsOpen] = useState(false);
  const { data: session } = useSession();
  const isPremium = session?.user?.premiumStatus === "premium";

  const dataRanges = useMemo(() => {
    const ranges: Record<string, { min: string; max: string }> = {};
    for (const config of ALL_FILTER_CONFIGS) {
      ranges[config.dataField as string] = computeDataRange(
        subnetData,
        config.dataField,
        config.displayScale ?? 1,
      );
    }
    return ranges;
  }, [subnetData]);

  function handleFilterChange(
    key: keyof ScreenerFilter,
    value: number | null,
    displayScale: number,
  ) {
    onFilterChange({
      ...filters,
      [key]: fromDisplayValue(value, displayScale),
    });
  }

  function handleImmunityChange(value: string) {
    const mapped =
      value === "all" ? null : value === "active" ? true : false;
    onFilterChange({ ...filters, immunity_active: mapped });
  }

  function renderFilterGroup(configs: FilterConfig[]) {
    return configs.map((config) => {
      const range = dataRanges[config.dataField as string];
      const scale = config.displayScale ?? 1;
      return (
        <RangeInput
          key={config.dataField as string}
          label={config.label}
          minValue={toDisplayValue(
            filters[config.minKey] as number | null,
            scale,
          )}
          maxValue={toDisplayValue(
            filters[config.maxKey] as number | null,
            scale,
          )}
          onMinChange={(val) =>
            handleFilterChange(config.minKey, val, scale)
          }
          onMaxChange={(val) =>
            handleFilterChange(config.maxKey, val, scale)
          }
          step={config.step}
          suffix={config.suffix}
          placeholderMin={range?.min}
          placeholderMax={range?.max}
        />
      );
    });
  }

  const immunityValue =
    filters.immunity_active === null
      ? "all"
      : filters.immunity_active
        ? "active"
        : "expired";

  const filterContent = (
    <div className="space-y-4">
      {/* Basic Filters */}
      <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
        Basic Filters
      </h3>
      {renderFilterGroup(BASIC_FILTER_CONFIGS)}

      {/* Divider */}
      <div className="border-t border-zinc-800" />

      {/* Advanced Filters */}
      <div className="flex items-center gap-2">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
          Advanced Filters
        </h3>
        <PremiumBadge />
      </div>

      {isPremium ? (
        <div className="space-y-4">
          {renderFilterGroup(ADVANCED_FILTER_CONFIGS)}

          {/* Immunity Status Toggle */}
          <div>
            <label
              htmlFor="immunity-filter"
              className="mb-1.5 block text-xs font-medium text-zinc-400"
            >
              Immunity Status
            </label>
            <select
              id="immunity-filter"
              value={immunityValue}
              onChange={(e) => handleImmunityChange(e.target.value)}
              className="min-h-[44px] w-full rounded-md border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-200 focus:outline-none focus:ring-2 focus:ring-violet-500"
            >
              <option value="all">All</option>
              <option value="active">Active (Immune)</option>
              <option value="expired">Expired</option>
            </select>
          </div>
        </div>
      ) : (
        <PremiumGate featureName="Advanced Filters">
          <div className="space-y-4">
            {renderFilterGroup(ADVANCED_FILTER_CONFIGS)}

            <div>
              <label
                htmlFor="immunity-filter-locked"
                className="mb-1.5 block text-xs font-medium text-zinc-400"
              >
                Immunity Status
              </label>
              <select
                id="immunity-filter-locked"
                disabled
                className="min-h-[44px] w-full rounded-md border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-200 opacity-50"
              >
                <option>All</option>
              </select>
            </div>
          </div>
        </PremiumGate>
      )}

      {activeFilterCount > 0 && (
        <Button
          variant="outline"
          size="sm"
          onClick={onReset}
          className="w-full"
        >
          Reset Filters
        </Button>
      )}

      <SavedScreenerPanel
        filters={filters}
        onLoadScreener={onFilterChange}
        activeFilterCount={activeFilterCount}
      />
    </div>
  );

  return (
    <div className="w-full shrink-0 lg:w-64">
      {/* Mobile toggle button — hidden on desktop */}
      <div className="lg:hidden">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setIsOpen(!isOpen)}
          className="mb-2"
          aria-expanded={isOpen}
          aria-controls="filter-panel"
        >
          Filters
          {activeFilterCount > 0 && (
            <span className="ml-1.5 rounded-full bg-[#8B5CF620] px-2 py-0.5 text-xs text-accent-primary">
              {activeFilterCount}
            </span>
          )}
        </Button>
      </div>

      {/* Filter panel — toggleable on mobile, always visible on desktop */}
      <div
        id="filter-panel"
        className={`${isOpen ? "block" : "hidden"} lg:block`}
        role="region"
        aria-label="Subnet filters"
      >
        <div className="sticky top-4 rounded-lg border border-zinc-800 bg-zinc-900/50 p-4">
          <h2 className="mb-4 hidden text-sm font-medium text-text-primary lg:block">
            Filters
            {activeFilterCount > 0 && (
              <span className="ml-1.5 rounded-full bg-[#8B5CF620] px-2 py-0.5 text-xs text-accent-primary">
                {activeFilterCount} active
              </span>
            )}
          </h2>
          {filterContent}
        </div>
      </div>
    </div>
  );
}
