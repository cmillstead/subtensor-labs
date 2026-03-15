"use client";

import { useState, useMemo } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// Page title set via companion layout.tsx (Client Components cannot export metadata)
import { AddressManager } from "@/components/portfolio/AddressManager";
import {
  PortfolioSummary,
  PortfolioSkeleton,
} from "@/components/portfolio/PortfolioSummary";
import {
  SubnetPositionList,
  SubnetPositionListSkeleton,
} from "@/components/portfolio/SubnetPositionList";
import {
  AllocationDonut,
  AllocationDonutSkeleton,
} from "@/components/portfolio/AllocationDonut";
import {
  PortfolioValueChart,
  PortfolioValueChartSkeleton,
} from "@/components/portfolio/PortfolioValueChart";
import { TimeRangeSelector } from "@/components/common/TimeRangeSelector";
import { usePortfolio } from "@/hooks/usePortfolio";
import { usePortfolioHistory } from "@/hooks/usePortfolioHistory";
import { usePersistedAddresses } from "@/hooks/usePersistedAddresses";
import type { TimeRange } from "@/types";

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 5 * 60 * 1000,
        refetchOnWindowFocus: true,
      },
    },
  });
}

let browserQueryClient: QueryClient | undefined;

function getQueryClient() {
  if (typeof window === "undefined") return makeQueryClient();
  browserQueryClient ??= makeQueryClient();
  return browserQueryClient;
}

function DashboardContent() {
  const {
    addresses: labeledAddresses,
    setAddresses: setLabeledAddresses,
    hydrated,
  } = usePersistedAddresses();
  const [timeRange, setTimeRange] = useState<TimeRange>("30d");

  // Extract plain address strings for API hooks
  const addressStrings = useMemo(
    () => labeledAddresses.map((a) => a.address),
    [labeledAddresses],
  );

  const { data, isLoading, isError, error } = usePortfolio(addressStrings);
  const history = usePortfolioHistory(addressStrings, timeRange);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-text-primary">
          Portfolio Dashboard
        </h1>
        <p className="mt-1 text-sm text-text-secondary">
          Enter your coldkey addresses to view your Bittensor position.
        </p>
      </header>

      <AddressManager
        addresses={labeledAddresses}
        onAddressesChange={setLabeledAddresses}
      />

      {hydrated && labeledAddresses.length === 0 && (
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-border py-16 text-center">
          <p className="text-lg text-text-secondary">No addresses added</p>
          <p className="mt-1 text-sm text-text-muted">
            Paste a coldkey address above to see your portfolio summary.
          </p>
        </div>
      )}

      {isLoading && (
        <>
          <PortfolioSkeleton />
          <section className="rounded-lg border border-border bg-surface p-5">
            <div className="mb-3">
              <h2 className="text-lg font-semibold text-text-primary">
                Allocation
              </h2>
            </div>
            <AllocationDonutSkeleton />
          </section>
          <section className="rounded-lg border border-border bg-surface p-5">
            <div className="mb-3">
              <h2 className="text-lg font-semibold text-text-primary">
                Portfolio Value
              </h2>
            </div>
            <PortfolioValueChartSkeleton />
          </section>
          <SubnetPositionListSkeleton />
        </>
      )}

      {isError && (
        <div
          className="rounded-lg border border-error/30 bg-error/5 p-4"
          role="alert"
        >
          <p className="text-sm text-error">
            {error?.message ?? "Failed to load portfolio data"}
          </p>
          <p className="mt-1 text-xs text-text-muted">
            Check that your address is correct and try again.
          </p>
        </div>
      )}

      {data?.data && (
        <>
          <PortfolioSummary
            portfolio={data.data}
            change24h={data.data.change_24h_pct}
            change7d={data.data.change_7d_pct}
          />

          {data.data.positions.length > 0 && (
            <>
              <section className="rounded-lg border border-border bg-surface p-5">
                <div className="mb-3">
                  <h2 className="text-lg font-semibold text-text-primary">
                    Allocation
                  </h2>
                </div>
                <AllocationDonut
                  positions={data.data.positions}
                  totalValueTao={data.data.total_value_tao}
                />
              </section>

              <section className="rounded-lg border border-border bg-surface p-5">
                <div className="mb-3 flex items-center justify-between">
                  <h2 className="text-lg font-semibold text-text-primary">
                    Portfolio Value
                  </h2>
                  <TimeRangeSelector
                    value={timeRange}
                    onChange={setTimeRange}
                  />
                </div>
                {history.isLoading ? (
                  <PortfolioValueChartSkeleton />
                ) : history.data?.data ? (
                  <PortfolioValueChart
                    points={history.data.data.points}
                    dataStart={history.data.data.data_start}
                    timeRange={timeRange}
                  />
                ) : null}
              </section>

              <section>
                <div className="mb-3 flex items-center gap-2">
                  <h2 className="text-lg font-semibold text-text-primary">
                    Subnet Positions
                  </h2>
                  <span className="rounded-full bg-surface-elevated px-2 py-0.5 font-mono text-xs text-text-secondary">
                    {data.data.positions.length}
                  </span>
                </div>
                <SubnetPositionList positions={data.data.positions} />
              </section>
            </>
          )}
        </>
      )}
    </div>
  );
}

export default function DashboardPage() {
  const queryClient = getQueryClient();

  return (
    <QueryClientProvider client={queryClient}>
      <DashboardContent />
    </QueryClientProvider>
  );
}
