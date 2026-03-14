"use client";

import { cn } from "@/lib/utils";

function formatRelativeTime(timestamp: string): string {
  const now = Date.now();
  const then = new Date(timestamp).getTime();
  const diffMs = now - then;
  const diffMin = Math.floor(diffMs / 60_000);
  const diffHr = Math.floor(diffMs / 3_600_000);

  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${diffMin} min ago`;
  if (diffHr < 24) return `${diffHr} hr ago`;
  return `${Math.floor(diffHr / 24)}d ago`;
}

interface LastUpdatedProps {
  timestamp: string;
  className?: string;
}

export function LastUpdated({ timestamp, className }: LastUpdatedProps) {
  return (
    <span
      className={cn("text-xs text-text-muted", className)}
      aria-label={`Last updated ${formatRelativeTime(timestamp)}`}
    >
      Updated {formatRelativeTime(timestamp)}
    </span>
  );
}
