"use client";

import { useMemo, useState } from "react";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  Legend,
} from "recharts";
import { cn } from "@/lib/utils";
import { formatTao } from "@/components/common/TaoAmount";
import type {
  SubnetEmissionForecast,
  SubnetEmissionForecastPoint,
  HalvingImpact,
  SubnetStakingMigration,
  PredictionHorizon,
} from "@/types";

const COLORS = {
  projection: "#8B5CF6", // Violet
  band68: "#3B82F6", // Blue
  band95: "#06B6D4", // Cyan
  inflow: "#10B981", // Emerald
  outflow: "#F43F5E", // Rose
  grid: "#27272A",
  axisText: "#A1A1AA",
  surfaceBg: "#18181B",
} as const;

const HORIZONS: { value: PredictionHorizon; label: string }[] = [
  { value: 30, label: "30D" },
  { value: 60, label: "60D" },
  { value: 90, label: "90D" },
];

/** Filter chart data to selected horizon */
export function filterChartData(
  chartData: SubnetEmissionForecastPoint[],
  horizon: PredictionHorizon,
): SubnetEmissionForecastPoint[] {
  return chartData.filter((p) => p.day <= horizon);
}

/** Build bar chart data for staking migration */
export function buildMigrationChartData(
  migrations: SubnetStakingMigration[],
): Array<{ netuid: number; label: string; value: number; direction: string }> {
  return migrations.map((m) => ({
    netuid: m.netuid,
    label: m.subnet_name ?? `SN${m.netuid}`,
    value: m.net_tao_inflow_30d,
    direction: m.direction,
  }));
}

/** Format days remaining as human-readable string */
export function formatDaysRemaining(days: number): string {
  if (days <= 0) return "Imminent";
  if (days >= 365) {
    const years = Math.floor(days / 365);
    const remainingDays = Math.round(days % 365);
    return remainingDays > 0
      ? `~${years}y ${remainingDays}d`
      : `~${years}y`;
  }
  return `~${Math.round(days)}d`;
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

interface EmissionChartTooltipProps {
  active?: boolean;
  payload?: Array<{ value: number; name: string; color: string }>;
  label?: number;
}

function EmissionChartTooltip({ active, payload, label }: EmissionChartTooltipProps) {
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
          {entry.name}: {Number(entry.value).toFixed(2)}%
        </p>
      ))}
    </div>
  );
}

interface MigrationTooltipProps {
  active?: boolean;
  payload?: Array<{ payload: { label: string; value: number; direction: string } }>;
}

function MigrationTooltip({ active, payload }: MigrationTooltipProps) {
  if (!active || !payload?.length) return null;
  const data = payload[0].payload;

  return (
    <div className="rounded-lg border border-border bg-surface p-3 shadow-lg">
      <p className="text-xs font-medium text-text-primary">{data.label}</p>
      <p
        className="font-mono text-sm"
        style={{ color: data.direction === "inflow" ? COLORS.inflow : COLORS.outflow }}
      >
        {data.direction === "inflow" ? "+" : ""}τ {formatTao(data.value, true)}
      </p>
    </div>
  );
}

interface EmissionTrajectoryChartProps {
  forecast: SubnetEmissionForecast;
  horizon: PredictionHorizon;
}

function EmissionTrajectoryChart({ forecast, horizon }: EmissionTrajectoryChartProps) {
  const data = useMemo(
    () => filterChartData(forecast.chart_data, horizon),
    [forecast.chart_data, horizon],
  );

  if (data.length === 0) return null;

  return (
    <div
      role="img"
      aria-label={`Emission share projection for SN${forecast.netuid} over ${horizon} days`}
    >
      <ResponsiveContainer width="100%" height={240}>
        <AreaChart data={data} margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
          <XAxis
            dataKey="day"
            tick={{ fill: COLORS.axisText, fontSize: 12 }}
            tickFormatter={(d: number) => `${d}d`}
          />
          <YAxis
            tick={{ fill: COLORS.axisText, fontSize: 12 }}
            tickFormatter={(v: number) => `${v.toFixed(1)}%`}
          />
          <Tooltip content={<EmissionChartTooltip />} />
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
            name="95% Lower"
            legendType="none"
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
            name="68% Lower"
            legendType="none"
          />

          {/* Projection line */}
          <Area
            type="monotone"
            dataKey="emission_share_pct"
            stroke={COLORS.projection}
            strokeWidth={2}
            fill={COLORS.projection}
            fillOpacity={0.05}
            name="Emission Share"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

interface StakingMigrationChartProps {
  migrations: SubnetStakingMigration[];
}

function StakingMigrationChart({ migrations }: StakingMigrationChartProps) {
  const data = useMemo(() => buildMigrationChartData(migrations), [migrations]);

  if (data.length === 0) {
    return (
      <p className="py-4 text-center text-sm text-text-muted">
        No staking migration data available.
      </p>
    );
  }

  return (
    <div
      role="img"
      aria-label="Network staking migration showing TAO inflows and outflows per subnet"
    >
      <ResponsiveContainer width="100%" height={Math.max(200, data.length * 32)}>
        <BarChart data={data} layout="vertical" margin={{ top: 5, right: 20, left: 60, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} horizontal={false} />
          <XAxis
            type="number"
            tick={{ fill: COLORS.axisText, fontSize: 12 }}
            tickFormatter={(v: number) => `τ${v >= 0 ? "+" : ""}${v.toFixed(0)}`}
          />
          <YAxis
            type="category"
            dataKey="label"
            tick={{ fill: COLORS.axisText, fontSize: 11 }}
            width={55}
          />
          <Tooltip content={<MigrationTooltip />} />
          <Bar dataKey="value" radius={[0, 4, 4, 0]}>
            {data.map((entry) => (
              <Cell
                key={`cell-${entry.netuid}`}
                fill={entry.direction === "inflow" ? COLORS.inflow : COLORS.outflow}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

interface HalvingCardProps {
  impact: HalvingImpact;
}

function HalvingCard({ impact }: HalvingCardProps) {
  return (
    <div className="rounded-lg border border-border bg-surface p-5">
      <h3 className="mb-3 text-lg font-semibold text-text-primary">
        Halving Countdown
      </h3>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        <div>
          <p className="text-xs text-text-secondary">Time Remaining</p>
          <p className="font-mono text-lg font-semibold text-violet-400">
            {formatDaysRemaining(impact.estimated_days_remaining)}
          </p>
        </div>
        <div>
          <p className="text-xs text-text-secondary">Blocks Remaining</p>
          <p className="font-mono text-lg font-semibold text-text-primary">
            {impact.blocks_remaining.toLocaleString()}
          </p>
        </div>
        <div>
          <p className="text-xs text-text-secondary">Yield Impact</p>
          <p className="font-mono text-lg font-semibold text-rose-400">
            {impact.estimated_yield_impact_pct.toFixed(0)}%
          </p>
        </div>
        <div>
          <p className="text-xs text-text-secondary">Current Emission/Day</p>
          <p className="font-mono text-sm text-text-primary">
            τ {formatTao(impact.current_emission_per_day_tao, true)}
          </p>
        </div>
        <div>
          <p className="text-xs text-text-secondary">Post-Halving/Day</p>
          <p className="font-mono text-sm text-text-secondary">
            τ {formatTao(impact.post_halving_emission_per_day_tao, true)}
          </p>
        </div>
      </div>
    </div>
  );
}

interface SubnetForecastTableProps {
  forecasts: SubnetEmissionForecast[];
}

function SubnetForecastTable({ forecasts }: SubnetForecastTableProps) {
  const sorted = useMemo(
    () => [...forecasts].sort((a, b) => b.current_emission_share_pct - a.current_emission_share_pct),
    [forecasts],
  );

  if (sorted.length === 0) {
    return (
      <p className="py-4 text-center text-sm text-text-muted">
        No subnet forecast data available.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left text-text-secondary">
            <th className="pb-2 font-medium">Subnet</th>
            <th className="pb-2 text-right font-medium">Emission Share</th>
            <th className="pb-2 text-right font-medium">Trend</th>
            <th className="pb-2 text-right font-medium">Momentum</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((f) => (
            <tr
              key={f.netuid}
              className="border-b border-border/50 hover:bg-elevated/50"
            >
              <td className="py-2">
                <span className="font-medium text-text-primary">
                  {f.subnet_name ?? `SN${f.netuid}`}
                </span>
              </td>
              <td className="py-2 text-right font-mono text-text-primary">
                {f.current_emission_share_pct.toFixed(2)}%
              </td>
              <td className="py-2 text-right">
                <span
                  className={cn(
                    "inline-flex items-center rounded px-1.5 py-0.5 text-xs font-medium",
                    f.ema_trend === "rising" && "bg-emerald-500/10 text-emerald-400",
                    f.ema_trend === "falling" && "bg-rose-500/10 text-rose-400",
                    f.ema_trend === "stable" && "bg-zinc-500/10 text-text-secondary",
                  )}
                >
                  {f.ema_trend === "rising" && "↑ Rising"}
                  {f.ema_trend === "falling" && "↓ Falling"}
                  {f.ema_trend === "stable" && "→ Stable"}
                </span>
              </td>
              <td className="py-2 text-right font-mono text-text-secondary">
                {f.momentum >= 0 ? "+" : ""}{f.momentum.toFixed(4)}/d
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

interface EmissionForecasterProps {
  subnetForecasts: SubnetEmissionForecast[];
  halvingImpact: HalvingImpact;
  stakingMigration: SubnetStakingMigration[];
  caveat: string;
  subnetsAnalyzed: number;
  subnetsSkipped: number;
}

function EmissionForecaster({
  subnetForecasts,
  halvingImpact,
  stakingMigration,
  caveat,
  subnetsAnalyzed,
  subnetsSkipped,
}: EmissionForecasterProps) {
  const [horizon, setHorizon] = useState<PredictionHorizon>(30);
  const [selectedSubnet, setSelectedSubnet] = useState<number | null>(null);

  // Default to the first subnet with chart data
  const activeSubnet = useMemo(() => {
    if (selectedSubnet !== null) {
      return subnetForecasts.find((f) => f.netuid === selectedSubnet);
    }
    return subnetForecasts[0] ?? null;
  }, [subnetForecasts, selectedSubnet]);

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

      {/* Halving impact card */}
      <HalvingCard impact={halvingImpact} />

      {/* Emission trajectory chart */}
      <section className="rounded-lg border border-border bg-surface p-5">
        <div className="mb-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-semibold text-text-primary">
              Emission Trajectory
            </h2>
            {subnetForecasts.length > 1 && (
              <select
                value={activeSubnet?.netuid ?? ""}
                onChange={(e) => setSelectedSubnet(Number(e.target.value))}
                className="rounded-md border border-border bg-elevated px-2 py-1 text-xs text-text-primary"
                aria-label="Select subnet for emission chart"
              >
                {subnetForecasts.map((f) => (
                  <option key={f.netuid} value={f.netuid}>
                    {f.subnet_name ?? `SN${f.netuid}`}
                  </option>
                ))}
              </select>
            )}
          </div>
          <HorizonSelector value={horizon} onChange={setHorizon} />
        </div>

        {activeSubnet ? (
          <EmissionTrajectoryChart forecast={activeSubnet} horizon={horizon} />
        ) : (
          <div className="flex h-[240px] items-center justify-center">
            <p className="text-sm text-text-muted">
              Insufficient historical data for emission projection.
            </p>
          </div>
        )}
      </section>

      {/* Staking migration chart */}
      <section className="rounded-lg border border-border bg-surface p-5">
        <h2 className="mb-3 text-lg font-semibold text-text-primary">
          Staking Migration (30d)
        </h2>
        <p className="mb-3 text-xs text-text-secondary">
          Net TAO inflows and outflows per subnet over the last 30 days.
        </p>
        <StakingMigrationChart migrations={stakingMigration} />
      </section>

      {/* Per-subnet forecast table */}
      <section className="rounded-lg border border-border bg-surface p-5">
        <h2 className="mb-3 text-lg font-semibold text-text-primary">
          Subnet Emission Forecasts
        </h2>
        <SubnetForecastTable forecasts={subnetForecasts} />
      </section>
    </div>
  );
}

function EmissionForecasterSkeleton() {
  return (
    <div className="space-y-6" aria-label="Loading emission forecast">
      {/* Caveat skeleton */}
      <div className="h-12 animate-pulse rounded-lg bg-elevated" />

      {/* Metrics skeleton */}
      <div className="flex gap-4">
        <div className="space-y-1">
          <div className="h-3 w-24 animate-pulse rounded bg-elevated" />
          <div className="h-6 w-16 animate-pulse rounded bg-elevated" />
        </div>
      </div>

      {/* Halving card skeleton */}
      <div className="rounded-lg border border-border bg-surface p-5">
        <div className="mb-3 h-5 w-36 animate-pulse rounded bg-elevated" />
        <div className="grid grid-cols-3 gap-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={`halving-skel-${i}`} className="space-y-1">
              <div className="h-3 w-20 animate-pulse rounded bg-elevated" />
              <div className="h-6 w-24 animate-pulse rounded bg-elevated" />
            </div>
          ))}
        </div>
      </div>

      {/* Chart skeleton */}
      <div className="rounded-lg border border-border bg-surface p-5">
        <div className="mb-3 flex items-center justify-between">
          <div className="h-5 w-36 animate-pulse rounded bg-elevated" />
          <div className="h-7 w-28 animate-pulse rounded bg-elevated" />
        </div>
        <div className="h-[240px] animate-pulse rounded bg-elevated" />
      </div>

      {/* Migration skeleton */}
      <div className="rounded-lg border border-border bg-surface p-5">
        <div className="mb-3 h-5 w-36 animate-pulse rounded bg-elevated" />
        <div className="h-[200px] animate-pulse rounded bg-elevated" />
      </div>

      {/* Table skeleton */}
      <div className="rounded-lg border border-border bg-surface p-5">
        <div className="mb-3 h-5 w-44 animate-pulse rounded bg-elevated" />
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={`table-skel-${i}`} className="flex items-center gap-4 py-2">
            <div className="h-4 w-20 animate-pulse rounded bg-elevated" />
            <div className="h-4 w-16 animate-pulse rounded bg-elevated" />
            <div className="h-4 w-16 animate-pulse rounded bg-elevated" />
            <div className="h-4 w-16 animate-pulse rounded bg-elevated" />
          </div>
        ))}
      </div>
    </div>
  );
}

export { EmissionForecaster, EmissionForecasterSkeleton };
