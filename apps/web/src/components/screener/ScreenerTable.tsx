"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import type { ScreenerSubnet, ScreenerSortField } from "@/types";
import { TaoAmount } from "@/components/common/TaoAmount";
import { SparklineChart } from "@/components/common/SparklineChart";
import { Button } from "@/components/ui/button";

interface SortState {
  field: ScreenerSortField;
  direction: "asc" | "desc";
}

interface ScreenerTableProps {
  subnets: ScreenerSubnet[] | undefined;
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
  onRetry: () => void;
}

type ColumnDef = {
  key: ScreenerSortField | "name" | "sparkline_emission" | "sparkline_price" | "subnet_age";
  label: string;
  sortField?: ScreenerSortField;
  hideOnTablet?: boolean;
};

const COLUMNS: ColumnDef[] = [
  { key: "name", label: "Subnet", sortField: undefined },
  { key: "miner_count", label: "Miners", sortField: "miner_count" },
  { key: "validator_count", label: "Validators", sortField: "validator_count" },
  { key: "registration_cost", label: "Reg Cost", sortField: "registration_cost" },
  { key: "emission_share", label: "Emission %", sortField: "emission_share" },
  { key: "alpha_price", label: "Alpha Price", sortField: "alpha_price" },
  { key: "sparkline_emission", label: "7d Emission", hideOnTablet: true },
  { key: "sparkline_price", label: "7d Price", hideOnTablet: true },
  { key: "subnet_age", label: "Age (days)" },
];

function formatInteger(value: number): string {
  return new Intl.NumberFormat("en-US").format(value);
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(2)}%`;
}

function SortIndicator({ field, sort }: { field: ScreenerSortField; sort: SortState }) {
  if (sort.field !== field) return null;
  return (
    <span className="ml-1" aria-label={sort.direction === "asc" ? "sorted ascending" : "sorted descending"}>
      {sort.direction === "asc" ? "▲" : "▼"}
    </span>
  );
}

function SkeletonRows() {
  return (
    <>
      {Array.from({ length: 8 }).map((_, i) => (
        <tr key={i} className="border-b border-border">
          {COLUMNS.map((col) => (
            <td
              key={col.key}
              className={`px-3 py-3 ${col.hideOnTablet ? "hidden lg:table-cell" : ""}`}
            >
              <div className="h-4 w-16 animate-pulse rounded bg-zinc-800" />
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}

export function ScreenerTable({
  subnets,
  isLoading,
  isError,
  error,
  onRetry,
}: ScreenerTableProps) {
  const [sort, setSort] = useState<SortState>({
    field: "emission_share",
    direction: "desc",
  });

  const sortedSubnets = useMemo(() => {
    if (!subnets) return [];
    return subnets.toSorted((a, b) => {
      const aVal = a[sort.field as keyof ScreenerSubnet];
      const bVal = b[sort.field as keyof ScreenerSubnet];
      if (typeof aVal === "number" && typeof bVal === "number") {
        return sort.direction === "asc" ? aVal - bVal : bVal - aVal;
      }
      return 0;
    });
  }, [subnets, sort]);

  function handleSort(field: ScreenerSortField) {
    setSort((prev) => ({
      field,
      direction: prev.field === field && prev.direction === "desc" ? "asc" : "desc",
    }));
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center gap-4 py-12 text-text-secondary" role="alert">
        <p>Failed to load subnet data{error?.message ? `: ${error.message}` : ""}</p>
        <Button variant="outline" onClick={onRetry}>
          Retry
        </Button>
      </div>
    );
  }

  if (!isLoading && subnets && subnets.length === 0) {
    return (
      <div className="py-12 text-center text-text-secondary">
        No subnet data available
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm" role="table">
        <thead>
          <tr className="border-b border-border text-left text-text-secondary">
            {COLUMNS.map((col) => (
              <th
                key={col.key}
                className={`px-3 py-3 font-medium ${col.hideOnTablet ? "hidden lg:table-cell" : ""} ${col.sortField ? "cursor-pointer select-none hover:text-text-primary" : ""}`}
                onClick={col.sortField ? () => handleSort(col.sortField!) : undefined}
                aria-sort={
                  col.sortField && sort.field === col.sortField
                    ? sort.direction === "asc"
                      ? "ascending"
                      : "descending"
                    : undefined
                }
              >
                {col.label}
                {col.sortField && <SortIndicator field={col.sortField} sort={sort} />}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {isLoading ? (
            <SkeletonRows />
          ) : (
            sortedSubnets.map((subnet) => (
              <tr
                key={subnet.netuid}
                className="border-b border-border transition-colors hover:bg-zinc-800/50"
              >
                <td className="px-3 py-3">
                  <Link
                    href={`/subnets/${subnet.netuid}`}
                    className="font-medium text-accent-primary hover:underline"
                  >
                    SN{subnet.netuid}
                    {subnet.name && (
                      <span className="ml-1.5 text-text-secondary">
                        · {subnet.name}
                      </span>
                    )}
                  </Link>
                </td>
                <td className="px-3 py-3 font-mono">
                  {formatInteger(subnet.miner_count)}
                </td>
                <td className="px-3 py-3 font-mono">
                  {formatInteger(subnet.validator_count)}
                </td>
                <td className="px-3 py-3">
                  <TaoAmount value={subnet.registration_cost} size="small" />
                </td>
                <td className="px-3 py-3 font-mono">
                  {formatPercent(subnet.emission_share)}
                </td>
                <td className="px-3 py-3">
                  <TaoAmount value={subnet.alpha_price} size="small" />
                </td>
                <td className="hidden px-3 py-3 lg:table-cell">
                  <SparklineChart data={subnet.sparkline_emission_7d} />
                </td>
                <td className="hidden px-3 py-3 lg:table-cell">
                  <SparklineChart data={subnet.sparkline_price_7d} />
                </td>
                <td className="px-3 py-3 font-mono">
                  {formatInteger(subnet.subnet_age_days)}
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
