"use client";

import { LineChart, Line, ResponsiveContainer } from "recharts";

interface SparklineChartProps {
  data: number[];
  color?: string;
  negativeColor?: string;
  width?: number;
  height?: number;
}

export function SparklineChart({
  data,
  color = "#8B5CF6",
  negativeColor = "#F43F5E",
  width = 80,
  height = 24,
}: SparklineChartProps) {
  if (data.length === 0) {
    return <div style={{ width, height }} aria-label="No trend data" />;
  }

  const isNegative = data.length >= 2 && data[data.length - 1] < data[0];
  const strokeColor = isNegative ? negativeColor : color;
  const chartData = data.map((value) => ({ value }));

  return (
    <div style={{ width, height }} aria-label="Trend sparkline">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData}>
          <Line
            type="monotone"
            dataKey="value"
            stroke={strokeColor}
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
