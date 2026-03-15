"use client";

import { useState } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { getQueryClient } from "@/lib/query-client";
import { ExploreAddressInput } from "@/components/portfolio/ExploreAddressInput";
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
import { usePortfolio } from "@/hooks/usePortfolio";

function ExploreContent() {
  const [address, setAddress] = useState<string | null>(null);
  const { data, isLoading, isError, error } = usePortfolio(
    address ? [address] : [],
  );

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-text-primary">
          Explore Portfolio
        </h1>
        <p className="mt-1 text-sm text-text-secondary">
          Paste any coldkey address to view its Bittensor portfolio. No account
          required.
        </p>
      </header>

      <ExploreAddressInput onSubmit={setAddress} isLoading={isLoading} />

      {!address && (
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-border py-16 text-center">
          <p className="text-lg text-text-secondary">
            Enter an address to get started
          </p>
          <p className="mt-1 text-sm text-text-muted">
            View any coldkey&apos;s portfolio — staking positions, subnet
            allocations, and delegation details.
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
            Check that the address is correct and try again.
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

export default function ExplorePage() {
  const queryClient = getQueryClient();

  return (
    <QueryClientProvider client={queryClient}>
      <ExploreContent />
    </QueryClientProvider>
  );
}
