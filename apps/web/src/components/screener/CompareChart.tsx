"use client";

import { useMemo } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { useSubnet } from "@/hooks/useSubnet";
import { SUBNET_COLORS } from "@/components/screener/SubnetCompare";
import type { SubnetHistoryPoint } from "@/types";

interface CompareChartProps {
  netuids: number[];
  subnetNames: string[];
  metric: "emission_share" | "alpha_price";
  label: string;
}

interface ChartDataPoint {
  time: string;
  [key: string]: string | number | null;
}

function prepareCompareChartData(
  histories: (SubnetHistoryPoint[] | undefined)[],
  netuids: number[],
  subnetNames: string[],
  metric: "emission_share" | "alpha_price",
): ChartDataPoint[] {
  // Collect all unique timestamps
  const timeSet = new Set<string>();
  for (const history of histories) {
    if (!history) continue;
    for (const point of history) {
      timeSet.add(point.time);
    }
  }

  const sortedTimes = Array.from(timeSet).sort();

  // Build lookup maps per subnet
  const lookups: Map<string, number>[] = histories.map((h) => {
    const map = new Map<string, number>();
    if (h) {
      for (const point of h) {
        map.set(point.time, point[metric]);
      }
    }
    return map;
  });

  return sortedTimes.map((time) => {
    const point: ChartDataPoint = {
      time: new Date(time).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
      }),
    };
    for (let i = 0; i < netuids.length; i++) {
      const key = subnetNames[i];
      point[key] = lookups[i].get(time) ?? null;
    }
    return point;
  });
}

interface CompareTooltipProps {
  active?: boolean;
  payload?: Array<{
    name: string;
    value: number;
    color: string;
  }>;
  label?: string;
  metric: "emission_share" | "alpha_price";
}

function CompareTooltip({ active, payload, label, metric }: CompareTooltipProps) {
  if (!active || !payload?.length) return null;

  return (
    <div className="rounded-lg border border-border bg-surface p-3 shadow-lg">
      <p className="text-xs font-medium text-text-primary">{label}</p>
      <div className="mt-1 space-y-0.5">
        {payload.map((entry) => (
          <p key={entry.name} className="font-mono text-xs" style={{ color: entry.color }}>
            {entry.name}:{" "}
            {metric === "emission_share"
              ? `${(entry.value * 100).toFixed(2)}%`
              : `τ ${entry.value.toFixed(4)}`}
          </p>
        ))}
      </div>
    </div>
  );
}

function CompareChart({ netuids, subnetNames, metric, label }: CompareChartProps) {
  // Fetch history for each subnet in parallel via TanStack Query
  const queries = [
    useSubnet(netuids[0], "30d"),
    useSubnet(netuids[1] ?? netuids[0], "30d"),
    useSubnet(netuids[2] ?? netuids[0], "30d"),
  ];

  // Only use the queries that correspond to actual netuids
  const activeQueries = queries.slice(0, netuids.length);
  const isLoading = activeQueries.some((q) => q.isLoading);
  const isError = activeQueries.some((q) => q.isError);

  const histories = activeQueries.map((q) => q.data?.data?.history);

  const chartData = useMemo(
    () => prepareCompareChartData(histories, netuids, subnetNames, metric),
    [histories, netuids, subnetNames, metric],
  );

  if (isLoading) {
    return (
      <div
        className="h-[300px] animate-pulse rounded-lg bg-elevated"
        aria-label={`Loading ${label} chart`}
      />
    );
  }

  if (isError) {
    return (
      <div className="flex h-[300px] items-center justify-center rounded-lg border border-border bg-surface" role="alert">
        <p className="text-sm text-red-400">Failed to load chart data.</p>
      </div>
    );
  }

  if (chartData.length === 0) {
    return (
      <div className="flex h-[300px] items-center justify-center rounded-lg border border-border bg-surface">
        <p className="text-sm text-text-secondary">No historical data available.</p>
      </div>
    );
  }

  const formatTick = (val: number) =>
    metric === "emission_share"
      ? `${(val * 100).toFixed(1)}%`
      : `τ${val.toFixed(2)}`;

  return (
    <div className="rounded-lg border border-border bg-surface p-4">
      <h3 className="mb-3 text-sm font-medium text-text-primary">{label}</h3>
      <div role="img" aria-label={`${label} comparison chart`}>
        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#27272A" />
            <XAxis
              dataKey="time"
              tick={{ fill: "#A1A1AA", fontSize: 11 }}
              stroke="#27272A"
            />
            <YAxis
              tickFormatter={formatTick}
              tick={{ fill: "#A1A1AA", fontSize: 11 }}
              stroke="#27272A"
            />
            <Tooltip content={<CompareTooltip metric={metric} />} />
            <Legend
              wrapperStyle={{ fontSize: 12, color: "#A1A1AA" }}
            />
            {subnetNames.map((name, i) => (
              <Line
                key={name}
                type="monotone"
                dataKey={name}
                stroke={SUBNET_COLORS[i]}
                strokeWidth={2}
                dot={false}
                connectNulls
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function CompareChartSkeleton() {
  return (
    <div className="h-[300px] animate-pulse rounded-lg bg-elevated" aria-label="Loading chart" />
  );
}

export { CompareChart, CompareChartSkeleton, prepareCompareChartData };
export type { CompareChartProps, ChartDataPoint };
