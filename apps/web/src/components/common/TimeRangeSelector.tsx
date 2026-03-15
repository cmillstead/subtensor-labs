"use client";

import { cn } from "@/lib/utils";
import type { TimeRange } from "@/types";

const RANGES: { value: TimeRange; label: string }[] = [
  { value: "7d", label: "7D" },
  { value: "30d", label: "30D" },
  { value: "90d", label: "90D" },
];

interface TimeRangeSelectorProps {
  value: TimeRange;
  onChange: (range: TimeRange) => void;
}

export function TimeRangeSelector({ value, onChange }: TimeRangeSelectorProps) {
  return (
    <div
      role="radiogroup"
      aria-label="Time range"
      className="inline-flex rounded-lg bg-elevated p-0.5"
    >
      {RANGES.map((range) => (
        <button
          key={range.value}
          role="radio"
          aria-checked={value === range.value}
          onClick={() => onChange(range.value)}
          className={cn(
            "rounded-md px-3 py-1 text-xs font-medium font-mono transition-colors",
            value === range.value
              ? "bg-accent text-white"
              : "text-text-secondary hover:text-text-primary",
          )}
        >
          {range.label}
        </button>
      ))}
    </div>
  );
}
