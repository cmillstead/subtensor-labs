"use client";

import { useMemo } from "react";
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { useRouter } from "next/navigation";
import type { ScreenerSubnet } from "@/types";

interface BubbleDataPoint {
  netuid: number;
  name: string;
  x: number;
  y: number;
  z: number;
  inflow: number;
}

interface SubnetBubbleChartProps {
  subnets: ScreenerSubnet[] | undefined;
  isLoading: boolean;
  isError?: boolean;
  error?: Error | null;
  onRetry?: () => void;
}

function prepareBubbleData(
  subnets: ScreenerSubnet[] | undefined,
): { data: BubbleDataPoint[]; excludedCount: number } {
  if (!subnets || subnets.length === 0) {
    return { data: [], excludedCount: 0 };
  }

  let excludedCount = 0;
  const data: BubbleDataPoint[] = [];

  for (const subnet of subnets) {
    if (
      subnet.alpha_price_change_7d === null ||
      subnet.net_tao_inflow === null
    ) {
      excludedCount++;
      continue;
    }

    data.push({
      netuid: subnet.netuid,
      name: subnet.name ?? `SN${subnet.netuid}`,
      x: subnet.emission_share * 100,
      y: subnet.alpha_price_change_7d,
      z: subnet.miner_count,
      inflow: subnet.net_tao_inflow,
    });
  }

  return { data, excludedCount };
}

const INFLOW_COLOR = "#10B981";
const OUTFLOW_COLOR = "#F43F5E";

interface CustomShapeProps {
  cx?: number;
  cy?: number;
  payload?: BubbleDataPoint;
  size?: number;
}

function BubbleShape({ cx, cy, payload, size }: CustomShapeProps) {
  if (cx == null || cy == null || !payload) return null;
  const radius = size ? Math.sqrt(size / Math.PI) : 6;
  const fill = payload.inflow >= 0 ? INFLOW_COLOR : OUTFLOW_COLOR;

  return (
    <circle
      cx={cx}
      cy={cy}
      r={radius}
      fill={fill}
      fillOpacity={0.7}
      stroke={fill}
      strokeWidth={1}
      style={{ cursor: "pointer" }}
    />
  );
}

interface BubbleTooltipProps {
  active?: boolean;
  payload?: Array<{ payload: BubbleDataPoint }>;
}

function BubbleTooltip({ active, payload }: BubbleTooltipProps) {
  if (!active || !payload?.[0]) return null;
  const point = payload[0].payload;

  return (
    <div className="rounded-lg border border-border bg-surface p-3 shadow-lg">
      <p className="text-sm font-medium text-text-primary">{point.name}</p>
      <p className="text-xs text-text-secondary">SN{point.netuid}</p>
      <div className="mt-2 space-y-1">
        <p className="font-mono text-xs text-text-secondary">
          Emission: {point.x.toFixed(2)}%
        </p>
        <p className="font-mono text-xs text-text-secondary">
          7d Change: {point.y >= 0 ? "+" : ""}
          {point.y.toFixed(1)}%
        </p>
        <p className="font-mono text-xs text-text-secondary">
          Miners: {point.z}
        </p>
        <p className="font-mono text-xs text-text-secondary">
          TAO Inflow:{" "}
          <span style={{ color: point.inflow >= 0 ? INFLOW_COLOR : OUTFLOW_COLOR }}>
            {point.inflow >= 0 ? "+" : ""}
            {point.inflow.toFixed(1)}τ
          </span>
        </p>
      </div>
    </div>
  );
}

function SubnetBubbleChart({ subnets, isLoading, isError, error, onRetry }: SubnetBubbleChartProps) {
  const router = useRouter();
  const { data, excludedCount } = useMemo(
    () => prepareBubbleData(subnets),
    [subnets],
  );

  if (isLoading) {
    return <SubnetBubbleChartSkeleton />;
  }

  if (isError) {
    return (
      <div
        className="flex h-[500px] flex-col items-center justify-center rounded-lg border border-border bg-surface"
        role="alert"
      >
        <p className="text-sm text-red-400">
          Failed to load screener data.
        </p>
        {error?.message && (
          <p className="mt-1 text-xs text-text-secondary">{error.message}</p>
        )}
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="mt-3 rounded-md bg-violet-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-violet-500"
          >
            Retry
          </button>
        )}
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div
        className="flex h-[500px] items-center justify-center rounded-lg border border-border bg-surface"
        role="img"
        aria-label="Bubble chart — no data available"
      >
        <p className="text-sm text-text-secondary">
          No subnets with sufficient data for bubble chart. Try adjusting your
          filters.
        </p>
      </div>
    );
  }

  const handleClick = (point: BubbleDataPoint) => {
    router.push(`/screener/${point.netuid}`);
  };

  return (
    <div>
      <div
        role="img"
        aria-label="Bubble chart showing subnet emission share vs 7-day price change, sized by miner count, colored by TAO inflow direction"
      >
        <ResponsiveContainer width="100%" height={500}>
          <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#27272A" />
            <XAxis
              type="number"
              dataKey="x"
              name="Emission Share"
              tickFormatter={(val: number) => `${val}%`}
              label={{
                value: "Emission Share (%)",
                position: "insideBottom",
                offset: -10,
                fill: "#A1A1AA",
                fontSize: 12,
              }}
              tick={{ fill: "#A1A1AA", fontSize: 12 }}
              stroke="#27272A"
            />
            <YAxis
              type="number"
              dataKey="y"
              name="7d Price Change"
              tickFormatter={(val: number) => `${val}%`}
              label={{
                value: "7d Price Change (%)",
                angle: -90,
                position: "insideLeft",
                offset: 10,
                fill: "#A1A1AA",
                fontSize: 12,
              }}
              tick={{ fill: "#A1A1AA", fontSize: 12 }}
              stroke="#27272A"
            />
            <ZAxis
              type="number"
              dataKey="z"
              range={[40, 400]}
              name="Miners"
            />
            <Tooltip content={<BubbleTooltip />} />
            <Scatter
              data={data}
              shape={<BubbleShape />}
              onClick={(entry: { payload?: BubbleDataPoint }) => {
                if (entry?.payload) {
                  handleClick(entry.payload);
                }
              }}
            />
          </ScatterChart>
        </ResponsiveContainer>
      </div>

      {/* Legend */}
      <div className="mt-3 flex items-center justify-center gap-6 text-xs text-text-secondary">
        <div className="flex items-center gap-1.5">
          <span
            className="inline-block h-3 w-3 rounded-full"
            style={{ backgroundColor: INFLOW_COLOR }}
          />
          <span>Net TAO Inflow (+)</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span
            className="inline-block h-3 w-3 rounded-full"
            style={{ backgroundColor: OUTFLOW_COLOR }}
          />
          <span>Net TAO Outflow (−)</span>
        </div>
        <span className="text-text-muted">Bubble size = miner count</span>
      </div>

      {excludedCount > 0 && (
        <p className="mt-2 text-center text-xs text-text-secondary">
          {excludedCount} {excludedCount === 1 ? "subnet" : "subnets"} not shown
          (insufficient price or inflow data)
        </p>
      )}
    </div>
  );
}

function SubnetBubbleChartSkeleton() {
  return (
    <div
      className="h-[500px] animate-pulse rounded-lg bg-elevated"
      aria-label="Loading bubble chart"
    />
  );
}

export {
  SubnetBubbleChart,
  SubnetBubbleChartSkeleton,
  prepareBubbleData,
};
export type { BubbleDataPoint, SubnetBubbleChartProps };
