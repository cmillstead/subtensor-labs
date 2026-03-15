"use client";

import { useCallback, useMemo, useState } from "react";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { cn } from "@/lib/utils";
import type { SubnetPosition } from "@/types";

const CHART_COLORS = [
  "#8B5CF6", // Violet
  "#3B82F6", // Blue
  "#06B6D4", // Cyan
  "#10B981", // Emerald
  "#F59E0B", // Amber
  "#F43F5E", // Rose
  "#EC4899", // Pink
  "#6366F1", // Indigo
];

const MAX_VISIBLE_SLICES = 8;

interface AllocationSlice {
  name: string;
  value: number;
  percentage: number;
  netuid: number | null;
  isOther: boolean;
  children?: AllocationSlice[];
}

interface AllocationDonutProps {
  positions: SubnetPosition[];
  totalValueTao: number;
  onSliceClick?: (netuid: number | null) => void;
  highlightedNetuid?: number | null;
  className?: string;
}

function computeAllocationData(
  positions: SubnetPosition[],
  totalValueTao: number,
): AllocationSlice[] {
  if (positions.length === 0 || totalValueTao <= 0) return [];

  // Aggregate by netuid (positions may have multiple entries per subnet)
  const byNetuid = new Map<number, { name: string; value: number }>();
  for (const p of positions) {
    const value = p.staked_tao + p.alpha_value_tao;
    const existing = byNetuid.get(p.netuid);
    if (existing) {
      existing.value += value;
    } else {
      byNetuid.set(p.netuid, {
        name: p.subnet_name ?? `SN${p.netuid}`,
        value,
      });
    }
  }

  const sorted = [...byNetuid.entries()]
    .map(([netuid, { name, value }]) => ({
      name,
      value,
      percentage: (value / totalValueTao) * 100,
      netuid,
      isOther: false,
    }))
    .toSorted((a, b) => b.value - a.value);

  if (sorted.length <= MAX_VISIBLE_SLICES) {
    return sorted;
  }

  const visible = sorted.slice(0, MAX_VISIBLE_SLICES);
  const remaining = sorted.slice(MAX_VISIBLE_SLICES);
  const otherValue = remaining.reduce((sum, s) => sum + s.value, 0);

  return [
    ...visible,
    {
      name: "Other",
      value: otherValue,
      percentage: (otherValue / totalValueTao) * 100,
      netuid: null,
      isOther: true,
      children: remaining,
    },
  ];
}

function formatTaoShort(value: number): string {
  if (value >= 1_000_000) return `τ ${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `τ ${(value / 1_000).toFixed(1)}K`;
  return `τ ${value.toFixed(2)}`;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{ payload: AllocationSlice }>;
}

function ChartTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload?.[0]) return null;
  const slice = payload[0].payload;

  return (
    <div className="rounded-lg border border-border bg-surface p-3 shadow-lg">
      <p className="text-sm font-medium text-text-primary">{slice.name}</p>
      <p className="font-mono text-sm text-text-secondary">
        {formatTaoShort(slice.value)}
      </p>
      <p className="font-mono text-sm text-text-secondary">
        {slice.percentage.toFixed(1)}%
      </p>
      {slice.isOther && slice.children && (
        <div className="mt-2 border-t border-border pt-2">
          {slice.children.map((child) => (
            <p
              key={child.netuid}
              className="text-xs text-text-muted"
            >
              {child.name}: {child.percentage.toFixed(1)}%
            </p>
          ))}
        </div>
      )}
    </div>
  );
}

function AllocationDonut({
  positions,
  totalValueTao,
  onSliceClick,
  highlightedNetuid,
  className,
}: AllocationDonutProps) {
  const slices = useMemo(
    () => computeAllocationData(positions, totalValueTao),
    [positions, totalValueTao],
  );

  const [activeIndex, setActiveIndex] = useState<number | null>(null);

  const handleClick = useCallback(
    (_: unknown, index: number) => {
      const slice = slices[index];
      onSliceClick?.(slice?.netuid ?? null);
    },
    [slices, onSliceClick],
  );

  if (slices.length === 0) return null;

  return (
    <div
      className={cn("flex flex-col items-center gap-4 md:flex-row md:items-start md:justify-center md:gap-8", className)}
      aria-label="Portfolio allocation chart showing subnet exposure percentages"
      role="figure"
    >
      <div className="relative h-[250px] w-[250px] shrink-0">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={slices}
              cx="50%"
              cy="50%"
              innerRadius={65}
              outerRadius={95}
              dataKey="value"
              nameKey="name"
              onClick={handleClick}
              onMouseEnter={(_, index) => setActiveIndex(index)}
              onMouseLeave={() => setActiveIndex(null)}
              style={{ cursor: onSliceClick ? "pointer" : "default" }}
            >
              {slices.map((slice, index) => {
                const isHighlighted =
                  highlightedNetuid != null &&
                  slice.netuid === highlightedNetuid;
                const isActive = activeIndex === index;
                return (
                  <Cell
                    key={slice.name}
                    fill={CHART_COLORS[index % CHART_COLORS.length]}
                    opacity={
                      highlightedNetuid != null && !isHighlighted
                        ? 0.4
                        : isActive
                          ? 0.85
                          : 1
                    }
                    stroke={isHighlighted ? "#FAFAFA" : "transparent"}
                    strokeWidth={isHighlighted ? 2 : 0}
                  />
                );
              })}
            </Pie>
            <Tooltip content={<ChartTooltip />} />
          </PieChart>
        </ResponsiveContainer>

        {/* Center label */}
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-xs text-text-secondary">Total</span>
          <span className="font-mono text-lg font-semibold text-text-primary">
            <span className="text-text-secondary">τ</span>{" "}
            {totalValueTao >= 1_000_000
              ? `${(totalValueTao / 1_000_000).toFixed(1)}M`
              : totalValueTao >= 1_000
                ? `${(totalValueTao / 1_000).toFixed(1)}K`
                : totalValueTao.toFixed(2)}
          </span>
        </div>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap justify-center gap-x-4 gap-y-2 md:flex-col md:flex-nowrap md:justify-start md:gap-y-3">
        {slices.map((slice, index) => (
          <button
            key={slice.name}
            type="button"
            className="flex items-center gap-2 rounded px-1 py-0.5 text-left transition-opacity hover:opacity-80"
            onClick={() => onSliceClick?.(slice.netuid ?? null)}
          >
            <span
              className="inline-block h-3 w-3 shrink-0 rounded-sm"
              style={{
                backgroundColor:
                  CHART_COLORS[index % CHART_COLORS.length],
              }}
            />
            <span className="text-sm text-text-primary">{slice.name}</span>
            <span className="font-mono text-sm text-text-secondary">
              {slice.percentage.toFixed(1)}%
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}

function AllocationDonutSkeleton() {
  return (
    <div
      className="flex flex-col items-center gap-4 md:flex-row md:items-start md:justify-center md:gap-8"
      aria-label="Loading allocation chart"
    >
      <div className="h-[250px] w-[250px] animate-pulse rounded-full bg-elevated" />
      <div className="flex flex-col gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="flex items-center gap-2">
            <div className="h-3 w-3 animate-pulse rounded-sm bg-elevated" />
            <div className="h-4 w-20 animate-pulse rounded bg-elevated" />
            <div className="h-4 w-10 animate-pulse rounded bg-elevated" />
          </div>
        ))}
      </div>
    </div>
  );
}

export { AllocationDonut, AllocationDonutSkeleton, computeAllocationData };
export type { AllocationSlice };
