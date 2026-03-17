"use client";

import { useMemo, useState } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { cn } from "@/lib/utils";
import { formatTao } from "@/components/common/TaoAmount";
import type {
  YieldChartPoint,
  SubnetYieldProjection,
  HorizonProjection,
  PredictionHorizon,
} from "@/types";

// Chart colors — dark theme
const COLORS = {
  projection: "#8B5CF6", // Violet
  band68: "#3B82F6", // Blue
  band95: "#06B6D4", // Cyan
  grid: "#27272A",
  axisText: "#A1A1AA",
  warning: "#F59E0B", // Amber
  surfaceBg: "#18181B", // zinc-900 — used for chart band punch-out
} as const;

const HORIZONS: { value: PredictionHorizon; label: string }[] = [
  { value: 30, label: "30D" },
  { value: 60, label: "60D" },
  { value: 90, label: "90D" },
];

/** Prepare chart data — filter to selected horizon */
export function prepareChartData(
  chartData: YieldChartPoint[],
  horizon: PredictionHorizon,
): YieldChartPoint[] {
  return chartData.filter((p) => p.day <= horizon);
}

/** Find the projection for the selected horizon */
export function findHorizonProjection(
  projections: HorizonProjection[],
  horizon: PredictionHorizon,
): HorizonProjection | undefined {
  return projections.find((p) => p.horizon_days === horizon);
}

interface HorizonSelectorProps {
  value: PredictionHorizon;
  onChange: (h: PredictionHorizon) => void;
}

function HorizonSelector({ value, onChange }: HorizonSelectorProps) {
  return (
    <div
      role="radiogroup"
      aria-label="Projection horizon"
      className="inline-flex rounded-lg bg-elevated p-0.5"
    >
      {HORIZONS.map((h) => (
        <button
          key={h.value}
          role="radio"
          aria-checked={value === h.value}
          onClick={() => onChange(h.value)}
          className={cn(
            "rounded-md px-3 py-1 text-xs font-medium font-mono transition-colors",
            value === h.value
              ? "bg-accent text-white"
              : "text-text-secondary hover:text-text-primary",
          )}
        >
          {h.label}
        </button>
      ))}
    </div>
  );
}

interface ChartTooltipProps {
  active?: boolean;
  payload?: Array<{ value: number; name: string; color: string }>;
  label?: number;
}

function ChartTooltip({ active, payload, label }: ChartTooltipProps) {
  if (!active || !payload?.length) return null;

  return (
    <div className="rounded-lg border border-border bg-surface p-3 shadow-lg">
      <p className="text-xs text-text-secondary">Day {label}</p>
      {payload.map((entry) => (
        <p
          key={entry.name}
          className="font-mono text-sm"
          style={{ color: entry.color }}
        >
          {entry.name}: τ {formatTao(entry.value, true)}
        </p>
      ))}
    </div>
  );
}

interface YieldFanChartProps {
  chartData: YieldChartPoint[];
  horizon: PredictionHorizon;
}

function YieldFanChart({ chartData, horizon }: YieldFanChartProps) {
  const data = useMemo(
    () => prepareChartData(chartData, horizon),
    [chartData, horizon],
  );

  if (data.length === 0) return null;

  return (
    <div
      role="img"
      aria-label={`Yield projection chart showing ${horizon}-day forecast with confidence bands`}
    >
      <ResponsiveContainer width="100%" height={320}>
        <AreaChart data={data} margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
          <XAxis
            dataKey="day"
            tick={{ fill: COLORS.axisText, fontSize: 12 }}
            tickFormatter={(d: number) => `${d}d`}
          />
          <YAxis
            tick={{ fill: COLORS.axisText, fontSize: 12 }}
            tickFormatter={(v: number) => `τ${v.toFixed(1)}`}
          />
          <Tooltip content={<ChartTooltip />} />
          <Legend />

          {/* 95% confidence band */}
          <Area
            type="monotone"
            dataKey="confidence_95_upper"
            stroke="none"
            fill={COLORS.band95}
            fillOpacity={0.1}
            name="95% Upper"
            legendType="none"
          />
          <Area
            type="monotone"
            dataKey="confidence_95_lower"
            stroke="none"
            fill={COLORS.surfaceBg}
            fillOpacity={1}
            name="95% Band"
          />

          {/* 68% confidence band */}
          <Area
            type="monotone"
            dataKey="confidence_68_upper"
            stroke="none"
            fill={COLORS.band68}
            fillOpacity={0.15}
            name="68% Upper"
            legendType="none"
          />
          <Area
            type="monotone"
            dataKey="confidence_68_lower"
            stroke="none"
            fill={COLORS.surfaceBg}
            fillOpacity={1}
            name="68% Band"
          />

          {/* Projection line */}
          <Area
            type="monotone"
            dataKey="projected_yield_tao"
            stroke={COLORS.projection}
            strokeWidth={2}
            fill={COLORS.projection}
            fillOpacity={0.05}
            name="Projected Yield"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

interface SubnetProjectionTableProps {
  projections: SubnetYieldProjection[];
}

function SubnetProjectionTable({ projections }: SubnetProjectionTableProps) {
  const sorted = useMemo(
    () => [...projections].sort((a, b) => b.projected_yield_tao - a.projected_yield_tao),
    [projections],
  );

  if (sorted.length === 0) {
    return (
      <p className="py-4 text-center text-sm text-text-muted">
        No subnet projections available.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left text-text-secondary">
            <th className="pb-2 font-medium">Subnet</th>
            <th className="pb-2 text-right font-medium">Staked</th>
            <th className="pb-2 text-right font-medium">Projected Yield</th>
            <th className="pb-2 text-right font-medium">68% Range</th>
            <th className="pb-2 text-right font-medium">R²</th>
            <th className="pb-2 text-right font-medium">Trend</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((proj) => (
            <tr
              key={proj.netuid}
              className="border-b border-border/50 hover:bg-elevated/50"
            >
              <td className="py-2">
                <span className="font-medium text-text-primary">
                  {proj.subnet_name ?? `SN${proj.netuid}`}
                </span>
                {proj.has_volatility_warning && (
                  <span
                    className="ml-2 inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-medium"
                    style={{ color: COLORS.warning, backgroundColor: `${COLORS.warning}20` }}
                    title="Subnet has less than 60 days of data — projections have higher uncertainty"
                  >
                    Volatile
                  </span>
                )}
              </td>
              <td className="py-2 text-right font-mono text-text-secondary">
                τ {formatTao(proj.current_stake_tao, true)}
              </td>
              <td className="py-2 text-right font-mono text-text-primary">
                τ {formatTao(proj.projected_yield_tao, true)}
              </td>
              <td className="py-2 text-right font-mono text-text-secondary">
                τ {formatTao(proj.confidence_68_lower, true)} – {formatTao(proj.confidence_68_upper, true)}
              </td>
              <td className="py-2 text-right font-mono text-text-secondary">
                {proj.r_squared.toFixed(2)}
              </td>
              <td className="py-2 text-right">
                <span
                  className={cn(
                    "font-mono text-xs",
                    proj.emission_trend_slope >= 0
                      ? "text-emerald-400"
                      : "text-rose-400",
                  )}
                >
                  {proj.emission_trend_slope >= 0 ? "↑" : "↓"}{" "}
                  {Math.abs(proj.emission_trend_slope).toFixed(4)}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

interface YieldProjectorProps {
  chartData: YieldChartPoint[];
  projections: HorizonProjection[];
  caveat: string;
  totalStakedTao: number;
  subnetsAnalyzed: number;
  subnetsSkipped: number;
}

function YieldProjector({
  chartData,
  projections,
  caveat,
  totalStakedTao,
  subnetsAnalyzed,
  subnetsSkipped,
}: YieldProjectorProps) {
  const [horizon, setHorizon] = useState<PredictionHorizon>(30);
  const currentProjection = findHorizonProjection(projections, horizon);

  return (
    <div className="space-y-6">
      {/* Caveat banner */}
      <div
        className="rounded-lg border border-amber-500/30 bg-amber-500/5 px-4 py-3"
        role="alert"
      >
        <p className="text-sm text-amber-200">{caveat}</p>
      </div>

      {/* Summary metrics */}
      <div className="flex flex-wrap items-center gap-4">
        <div>
          <p className="text-xs text-text-secondary">Total Staked</p>
          <p className="font-mono text-lg font-semibold text-text-primary">
            τ {formatTao(totalStakedTao, true)}
          </p>
        </div>
        {currentProjection && (
          <div>
            <p className="text-xs text-text-secondary">
              Projected Yield ({horizon}d)
            </p>
            <p className="font-mono text-lg font-semibold text-violet-400">
              τ {formatTao(currentProjection.total_projected_yield_tao, true)}
            </p>
          </div>
        )}
        <div>
          <p className="text-xs text-text-secondary">Subnets Analyzed</p>
          <p className="font-mono text-lg font-semibold text-text-primary">
            {subnetsAnalyzed}
            {subnetsSkipped > 0 && (
              <span className="ml-1 text-sm font-normal text-text-muted">
                ({subnetsSkipped} skipped)
              </span>
            )}
          </p>
        </div>
      </div>

      {/* Chart section */}
      <section className="rounded-lg border border-border bg-surface p-5">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-text-primary">
            Yield Projection
          </h2>
          <HorizonSelector value={horizon} onChange={setHorizon} />
        </div>
        {chartData.length > 0 ? (
          <YieldFanChart chartData={chartData} horizon={horizon} />
        ) : (
          <div className="flex h-[320px] items-center justify-center">
            <p className="text-sm text-text-muted">
              Insufficient historical data for chart projection.
            </p>
          </div>
        )}
      </section>

      {/* Per-subnet table */}
      <section className="rounded-lg border border-border bg-surface p-5">
        <h2 className="mb-3 text-lg font-semibold text-text-primary">
          Per-Subnet Forecast ({horizon}d)
        </h2>
        <SubnetProjectionTable
          projections={currentProjection?.subnet_projections ?? []}
        />
      </section>
    </div>
  );
}

function YieldProjectorSkeleton() {
  return (
    <div className="space-y-6" aria-label="Loading yield projections">
      {/* Caveat skeleton */}
      <div className="h-12 animate-pulse rounded-lg bg-elevated" />

      {/* Metrics skeleton */}
      <div className="flex gap-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="space-y-1">
            <div className="h-3 w-16 animate-pulse rounded bg-elevated" />
            <div className="h-6 w-24 animate-pulse rounded bg-elevated" />
          </div>
        ))}
      </div>

      {/* Chart skeleton */}
      <div className="rounded-lg border border-border bg-surface p-5">
        <div className="mb-3 flex items-center justify-between">
          <div className="h-5 w-32 animate-pulse rounded bg-elevated" />
          <div className="h-7 w-28 animate-pulse rounded bg-elevated" />
        </div>
        <div className="h-[320px] animate-pulse rounded bg-elevated" />
      </div>

      {/* Table skeleton */}
      <div className="rounded-lg border border-border bg-surface p-5">
        <div className="mb-3 h-5 w-40 animate-pulse rounded bg-elevated" />
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="flex items-center gap-4 py-2">
            <div className="h-4 w-24 animate-pulse rounded bg-elevated" />
            <div className="h-4 w-16 animate-pulse rounded bg-elevated" />
            <div className="h-4 w-16 animate-pulse rounded bg-elevated" />
            <div className="h-4 w-24 animate-pulse rounded bg-elevated" />
          </div>
        ))}
      </div>
    </div>
  );
}

export { YieldProjector, YieldProjectorSkeleton };
