"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { SubnetHistoryPoint } from "@/types";

function formatDate(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

interface SubnetChartProps {
  data: SubnetHistoryPoint[];
  dataKey: "emission_share" | "alpha_price" | "miner_count";
  label: string;
  color?: string;
  formatValue?: (v: number) => string;
}

export function SubnetChart({
  data,
  dataKey,
  label,
  color = "#8B5CF6",
  formatValue = (v) => String(v),
}: SubnetChartProps) {
  const gradientId = `gradient-${dataKey}`;

  return (
    <div>
      <h3 className="mb-2 text-sm font-medium text-text-secondary">{label}</h3>
      <div className="rounded-lg border border-border bg-surface p-3">
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={data}>
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={color} stopOpacity={0.3} />
                <stop offset="95%" stopColor={color} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
            <XAxis
              dataKey="time"
              tickFormatter={formatDate}
              tick={{ fill: "#71717a", fontSize: 11 }}
              axisLine={{ stroke: "#27272a" }}
              tickLine={false}
            />
            <YAxis
              tickFormatter={formatValue}
              tick={{ fill: "#71717a", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              width={60}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "#18181b",
                border: "1px solid #27272a",
                borderRadius: "8px",
                color: "#fafafa",
                fontSize: 12,
              }}
              labelFormatter={formatDate}
              formatter={(value: number) => [formatValue(value), label]}
            />
            <Area
              type="monotone"
              dataKey={dataKey}
              stroke={color}
              strokeWidth={2}
              fill={`url(#${gradientId})`}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
