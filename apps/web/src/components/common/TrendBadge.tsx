"use client";

import { cn } from "@/lib/utils";

interface TrendBadgeProps {
  value: number | null;
  className?: string;
}

export function TrendBadge({ value, className }: TrendBadgeProps) {
  if (value == null) {
    return (
      <span
        className={cn("font-mono text-sm text-text-muted", className)}
        aria-label="No change data available"
      >
        —
      </span>
    );
  }

  const isPositive = value > 0;
  const isNegative = value < 0;
  const arrow = isPositive ? "↑" : isNegative ? "↓" : "→";
  const sign = isPositive ? "+" : "";
  const formatted = `${sign}${value.toFixed(1)}%`;
  const direction = isPositive ? "up" : isNegative ? "down" : "unchanged";

  const colorClass = isPositive
    ? "text-success"
    : isNegative
      ? "text-error"
      : "text-text-muted";

  return (
    <span
      className={cn("font-mono text-sm", colorClass, className)}
      aria-label={`${direction} ${Math.abs(value).toFixed(1)}%`}
    >
      {arrow} {formatted}
    </span>
  );
}
