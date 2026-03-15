"use client";

import { useMemo, useState } from "react";
import type { ScreenerFilter, ScreenerSubnet } from "@/types";
import { RangeInput } from "./RangeInput";
import { Button } from "@/components/ui/button";

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

const FILTER_CONFIGS: FilterConfig[] = [
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

function computeDataRange(
  subnets: ScreenerSubnet[] | undefined,
  field: keyof ScreenerSubnet,
  displayScale: number,
): { min: string; max: string } {
  if (!subnets || subnets.length === 0) return { min: "Min", max: "Max" };
  const values = subnets.map((s) => s[field] as number);
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

  const dataRanges = useMemo(() => {
    const ranges: Record<string, { min: string; max: string }> = {};
    for (const config of FILTER_CONFIGS) {
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

  const filterContent = (
    <div className="space-y-4">
      {FILTER_CONFIGS.map((config) => {
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
      })}

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
