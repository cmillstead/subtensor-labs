"use client";

import { cn } from "@/lib/utils";

const sizeClasses = {
  large: "text-3xl font-bold",
  medium: "text-xl font-semibold",
  small: "text-sm font-medium",
} as const;

function formatTao(value: number, abbreviate: boolean): string {
  if (abbreviate) {
    if (value >= 1_000_000) {
      return `${(value / 1_000_000).toFixed(1)}M`;
    }
    if (value >= 1_000) {
      return `${(value / 1_000).toFixed(1)}K`;
    }
  }
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

function formatUsd(value: number): string {
  if (value >= 1_000) {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 0,
    }).format(value);
  }
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

interface TaoAmountProps {
  value: number;
  size?: "large" | "medium" | "small";
  abbreviate?: boolean;
  showUsd?: boolean;
  usdPrice?: number;
  className?: string;
}

export function TaoAmount({
  value,
  size = "medium",
  abbreviate = false,
  showUsd = false,
  usdPrice,
  className,
}: TaoAmountProps) {
  const formatted = formatTao(value, abbreviate);
  const fullFormatted = new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);

  return (
    <span
      className={cn("font-mono text-text-primary", sizeClasses[size], className)}
      aria-label={`${fullFormatted} TAO`}
    >
      <span className="text-text-secondary">τ</span> {formatted}
      {showUsd && usdPrice != null && (
        <span className="ml-2 text-text-secondary">
          {formatUsd(value * usdPrice)}
        </span>
      )}
    </span>
  );
}
