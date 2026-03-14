"use client";

import { cn } from "@/lib/utils";
import { TaoAmount } from "@/components/common/TaoAmount";
import { TrendBadge } from "@/components/common/TrendBadge";
import { LastUpdated } from "@/components/common/LastUpdated";
import type { PortfolioResult } from "@/types";

interface PortfolioSummaryProps {
  portfolio: PortfolioResult;
  change24h?: number | null;
  change7d?: number | null;
  className?: string;
}

function PortfolioSkeleton() {
  return (
    <div
      className="animate-pulse rounded-lg border border-border bg-surface p-5"
      aria-label="Loading portfolio summary"
    >
      <div className="mb-2 h-4 w-32 rounded bg-elevated" />
      <div className="mb-3 h-10 w-48 rounded bg-elevated" />
      <div className="flex gap-4">
        <div className="h-4 w-20 rounded bg-elevated" />
        <div className="h-4 w-24 rounded bg-elevated" />
        <div className="h-4 w-28 rounded bg-elevated" />
      </div>
    </div>
  );
}

function PortfolioSummary({
  portfolio,
  change24h,
  change7d,
  className,
}: PortfolioSummaryProps) {
  const subnetCount = portfolio.positions.length;

  return (
    <section
      className={cn(
        "rounded-lg border border-border p-5",
        className,
      )}
      style={{
        background:
          "linear-gradient(135deg, #8B5CF610, #3B82F610), #131316",
      }}
      aria-label={`Portfolio summary showing total value of ${portfolio.total_value_tao.toLocaleString("en-US", { minimumFractionDigits: 2 })} TAO`}
    >
      <p className="mb-1 text-sm text-text-secondary">Total Portfolio Value</p>

      <div className="mb-3 flex items-baseline gap-3">
        <TaoAmount value={portfolio.total_value_tao} size="large" />
        {change24h != null && (
          <TrendBadge value={change24h} />
        )}
      </div>

      <div className="flex flex-wrap items-center gap-4 text-sm">
        <span className="text-text-secondary">
          <span className="font-mono text-text-primary">{subnetCount}</span>{" "}
          {subnetCount === 1 ? "subnet" : "subnets"}
        </span>

        {change7d != null && (
          <span className="flex items-center gap-1 text-text-secondary">
            7d: <TrendBadge value={change7d} />
          </span>
        )}

        <LastUpdated timestamp={portfolio.last_updated} />
      </div>
    </section>
  );
}

export { PortfolioSummary, PortfolioSkeleton };
