"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { PortfolioHistoryPoint, TimeRange } from "@/types";

interface PortfolioValueChartProps {
  points: PortfolioHistoryPoint[];
  dataStart: string | null;
  timeRange: TimeRange;
}

/** Format a TAO value with abbreviation for axis labels. */
export function formatTaoAxis(value: number): string {
  if (value >= 1_000_000) return `τ ${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `τ ${(value / 1_000).toFixed(1)}K`;
  return `τ ${value.toFixed(0)}`;
}

/** Format a timestamp for X-axis based on time range. */
export function formatDateAxis(iso: string, timeRange: TimeRange): string {
  const d = new Date(iso);
  if (timeRange === "7d") {
    return new Intl.DateTimeFormat("en-US", {
      weekday: "short",
      hour: "numeric",
    }).format(d);
  }
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
  }).format(d);
}

function ChartTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { value: number; payload: PortfolioHistoryPoint }[];
}) {
  if (!active || !payload?.length) return null;
  const point = payload[0];
  const d = new Date(point.payload.time);
  return (
    <div className="rounded-lg border border-border bg-elevated p-3 text-sm shadow-lg">
      <p className="text-text-secondary">
        {new Intl.DateTimeFormat("en-US", {
          month: "short",
          day: "numeric",
          year: "numeric",
          hour: "numeric",
          minute: "2-digit",
        }).format(d)}
      </p>
      <p className="font-mono text-text-primary">
        τ {point.value.toLocaleString("en-US", { maximumFractionDigits: 2 })}
      </p>
    </div>
  );
}

export function PortfolioValueChart({
  points,
  dataStart,
  timeRange,
}: PortfolioValueChartProps) {
  if (points.length === 0) {
    return (
      <div className="flex h-[300px] items-center justify-center">
        <p className="text-text-secondary">
          No historical data available yet. Portfolio tracking will begin
          shortly.
        </p>
      </div>
    );
  }

  return (
    <div
      role="figure"
      aria-label="Historical portfolio value chart showing total value in TAO over time"
    >
      <div className="h-[300px]">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={points}
            margin={{ top: 5, right: 5, left: 10, bottom: 5 }}
          >
            <defs>
              <linearGradient
                id="portfolioGradient"
                x1="0"
                y1="0"
                x2="0"
                y2="1"
              >
                <stop offset="5%" stopColor="#8B5CF6" stopOpacity={0.2} />
                <stop offset="95%" stopColor="#8B5CF6" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#27272A" />
            <XAxis
              dataKey="time"
              tickFormatter={(v: string) => formatDateAxis(v, timeRange)}
              stroke="#A1A1AA"
              tick={{
                fontFamily: "JetBrains Mono, monospace",
                fontSize: 12,
              }}
            />
            <YAxis
              tickFormatter={formatTaoAxis}
              stroke="#A1A1AA"
              tick={{
                fontFamily: "JetBrains Mono, monospace",
                fontSize: 12,
              }}
            />
            <Tooltip content={<ChartTooltip />} />
            <Area
              type="monotone"
              dataKey="total_value_tao"
              stroke="#8B5CF6"
              strokeWidth={2}
              fill="url(#portfolioGradient)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-2 flex items-center justify-between">
        <p className="text-xs text-text-muted">
          Based on current positions
        </p>
        {dataStart && (
          <p className="text-xs text-text-muted">
            Tracking since{" "}
            {new Intl.DateTimeFormat("en-US", {
              month: "short",
              day: "numeric",
              year: "numeric",
            }).format(new Date(dataStart))}
          </p>
        )}
      </div>
    </div>
  );
}

export function PortfolioValueChartSkeleton() {
  return (
    <div aria-label="Loading portfolio value chart">
      <div className="h-[300px] animate-pulse rounded-lg bg-elevated" />
      <div className="mt-2 flex justify-end gap-1">
        <div className="h-5 w-8 animate-pulse rounded-md bg-elevated" />
        <div className="h-5 w-8 animate-pulse rounded-md bg-elevated" />
        <div className="h-5 w-8 animate-pulse rounded-md bg-elevated" />
      </div>
    </div>
  );
}
