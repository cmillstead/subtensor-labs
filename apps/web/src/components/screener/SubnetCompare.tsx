"use client";

import { useMemo } from "react";
import type { ScreenerSubnet } from "@/types";
import { TaoAmount } from "@/components/common/TaoAmount";
import { CompareChart } from "@/components/screener/CompareChart";
import { Button } from "@/components/ui/button";

interface SubnetCompareProps {
  subnets: ScreenerSubnet[];
  onClose: () => void;
}

interface MetricDef {
  key: string;
  label: string;
  getValue: (s: ScreenerSubnet) => number | null;
  format: (value: number | null) => React.ReactNode;
  higherIsBetter: boolean;
}

const SUBNET_COLORS = ["#8B5CF6", "#3B82F6", "#10B981"] as const;

function formatPercent(value: number | null): React.ReactNode {
  if (value === null) return <span className="text-text-muted">—</span>;
  return `${(value * 100).toFixed(2)}%`;
}

function formatPercentDelta(value: number | null): React.ReactNode {
  if (value === null) return <span className="text-text-muted">—</span>;
  return `${value >= 0 ? "+" : ""}${value.toFixed(1)}%`;
}

function formatInteger(value: number | null): React.ReactNode {
  if (value === null) return <span className="text-text-muted">—</span>;
  return new Intl.NumberFormat("en-US").format(value);
}

function formatTaoInline(value: number | null): React.ReactNode {
  if (value === null) return <span className="text-text-muted">—</span>;
  return <TaoAmount value={value} size="small" />;
}

const METRICS: MetricDef[] = [
  { key: "miner_count", label: "Miners", getValue: (s) => s.miner_count, format: formatInteger, higherIsBetter: true },
  { key: "validator_count", label: "Validators", getValue: (s) => s.validator_count, format: formatInteger, higherIsBetter: true },
  { key: "registration_cost", label: "Reg Cost", getValue: (s) => s.registration_cost, format: formatTaoInline, higherIsBetter: false },
  { key: "emission_share", label: "Emission %", getValue: (s) => s.emission_share, format: formatPercent, higherIsBetter: true },
  { key: "alpha_price", label: "Alpha Price", getValue: (s) => s.alpha_price, format: formatTaoInline, higherIsBetter: true },
  { key: "alpha_market_cap", label: "Market Cap", getValue: (s) => s.alpha_market_cap, format: formatTaoInline, higherIsBetter: true },
  { key: "fill_rate", label: "Fill Rate", getValue: (s) => s.fill_rate, format: formatPercent, higherIsBetter: true },
  { key: "owner_take_rate", label: "Owner Take", getValue: (s) => s.owner_take_rate, format: formatPercent, higherIsBetter: false },
  { key: "tao_reserves", label: "TAO Reserves", getValue: (s) => s.tao_reserves, format: formatTaoInline, higherIsBetter: true },
  { key: "alpha_price_change_7d", label: "7d Price Change", getValue: (s) => s.alpha_price_change_7d, format: formatPercentDelta, higherIsBetter: true },
  { key: "net_tao_inflow", label: "Net TAO Inflow", getValue: (s) => s.net_tao_inflow, format: formatTaoInline, higherIsBetter: true },
];

function determineBestValues(
  subnets: ScreenerSubnet[],
  metrics: MetricDef[],
): Map<string, number | null> {
  const bestMap = new Map<string, number | null>();

  for (const metric of metrics) {
    let bestIdx: number | null = null;
    let bestVal: number | null = null;

    for (let i = 0; i < subnets.length; i++) {
      const val = metric.getValue(subnets[i]);
      if (val === null) continue;
      if (bestVal === null) {
        bestVal = val;
        bestIdx = i;
      } else if (metric.higherIsBetter ? val > bestVal : val < bestVal) {
        bestVal = val;
        bestIdx = i;
      }
    }

    bestMap.set(metric.key, bestIdx);
  }

  return bestMap;
}

function SubnetCompare({ subnets, onClose }: SubnetCompareProps) {
  const bestValues = useMemo(
    () => determineBestValues(subnets, METRICS),
    [subnets],
  );

  if (subnets.length === 0) {
    return (
      <div className="py-12 text-center text-text-secondary">
        No subnets selected for comparison.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-text-primary">
          Subnet Comparison
        </h2>
        <Button
          variant="outline"
          size="sm"
          onClick={onClose}
        >
          Back to Screener
        </Button>
      </div>

      {/* Metrics comparison table */}
      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-sm" role="table">
          <thead>
            <tr className="border-b border-border bg-elevated">
              <th className="px-4 py-3 text-left font-medium text-text-secondary">
                Metric
              </th>
              {subnets.map((s, i) => (
                <th
                  key={s.netuid}
                  className="px-4 py-3 text-left font-medium"
                  style={{ color: SUBNET_COLORS[i] }}
                >
                  SN{s.netuid}
                  {s.name && (
                    <span className="ml-1.5 text-text-secondary">
                      · {s.name}
                    </span>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {METRICS.map((metric) => {
              const bestIdx = bestValues.get(metric.key);
              return (
                <tr
                  key={metric.key}
                  className="border-b border-border last:border-b-0"
                >
                  <td className="px-4 py-2.5 font-medium text-text-secondary">
                    {metric.label}
                  </td>
                  {subnets.map((s, i) => (
                    <td
                      key={s.netuid}
                      className={`px-4 py-2.5 font-mono ${
                        bestIdx === i ? "text-emerald-400" : "text-text-primary"
                      }`}
                    >
                      {metric.format(metric.getValue(s))}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Historical overlay charts */}
      <div className="grid gap-6 2xl:grid-cols-2">
        <CompareChart
          netuids={subnets.map((s) => s.netuid)}
          subnetNames={subnets.map((s) => s.name ?? `SN${s.netuid}`)}
          metric="emission_share"
          label="Emission Share"
        />
        <CompareChart
          netuids={subnets.map((s) => s.netuid)}
          subnetNames={subnets.map((s) => s.name ?? `SN${s.netuid}`)}
          metric="alpha_price"
          label="Alpha Price"
        />
      </div>
    </div>
  );
}

function SubnetCompareSkeleton() {
  return (
    <div className="space-y-6">
      <div className="h-8 w-48 animate-pulse rounded bg-elevated" />
      <div className="h-[300px] animate-pulse rounded-lg bg-elevated" aria-label="Loading comparison" />
      <div className="grid gap-6 2xl:grid-cols-2">
        <div className="h-[300px] animate-pulse rounded-lg bg-elevated" />
        <div className="h-[300px] animate-pulse rounded-lg bg-elevated" />
      </div>
    </div>
  );
}

export { SubnetCompare, SubnetCompareSkeleton, determineBestValues, SUBNET_COLORS, METRICS };
export type { SubnetCompareProps, MetricDef };
