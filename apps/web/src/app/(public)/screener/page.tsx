"use client";

import { useState } from "react";
import { useSession } from "next-auth/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { getQueryClient } from "@/lib/query-client";
import { LastUpdated } from "@/components/common/LastUpdated";
import { PremiumGate } from "@/components/common/PremiumGate";
import { ScreenerTable } from "@/components/screener/ScreenerTable";
import { FilterPanel } from "@/components/screener/FilterPanel";
import { ScreenerCSVExport } from "@/components/screener/ScreenerCSVExport";
import { SubnetBubbleChart } from "@/components/screener/SubnetBubbleChart";
import { ViewToggle } from "@/components/screener/ViewToggle";
import type { ScreenerView } from "@/components/screener/ViewToggle";
import { useScreener } from "@/hooks/useScreener";
import { useScreenerFilters } from "@/hooks/useScreenerFilters";

function ScreenerContent() {
  const { data: session } = useSession();
  const isPremium = session?.user?.premiumStatus === "premium";
  const [view, setView] = useState<ScreenerView>("table");

  const { data, isLoading, isError, error, refetch } = useScreener();
  const subnets = data?.data?.subnets;
  const totalCount = data?.data?.subnet_count;

  const {
    filters,
    setFilters,
    filteredSubnets,
    activeFilterCount,
    resetFilters,
  } = useScreenerFilters(subnets);

  const filteredCount = filteredSubnets.length;
  const hasActiveFilters = activeFilterCount > 0;
  const displaySubnets = hasActiveFilters ? filteredSubnets : subnets;

  return (
    <div className="space-y-6">
      <header className="flex items-end justify-between">
        <div className="flex items-end gap-4">
          <div>
            <h1 className="text-2xl font-semibold text-text-primary">
              Subnet Screener
            </h1>
            <p className="mt-1 text-sm text-text-secondary">
              Browse and compare all active Bittensor subnets.
            </p>
          </div>
          <ViewToggle view={view} onViewChange={setView} />
        </div>
        <div className="flex items-center gap-3">
          <ScreenerCSVExport
            subnets={displaySubnets}
            isLoading={isLoading}
          />
          {data?.meta?.last_updated && (
            <LastUpdated timestamp={data.meta.last_updated} />
          )}
        </div>
      </header>

      {totalCount !== undefined && (
        <p className="text-sm text-text-secondary">
          {hasActiveFilters
            ? `Showing ${filteredCount} of ${totalCount} ${totalCount === 1 ? "subnet" : "subnets"}`
            : `Showing ${totalCount} ${totalCount === 1 ? "subnet" : "subnets"}`}
        </p>
      )}

      <div className="flex gap-6">
        <FilterPanel
          filters={filters}
          onFilterChange={setFilters}
          onReset={resetFilters}
          activeFilterCount={activeFilterCount}
          subnetData={subnets}
        />

        <div className="min-w-0 flex-1">
          {view === "table" ? (
            <ScreenerTable
              subnets={displaySubnets}
              isLoading={isLoading}
              isError={isError}
              error={error}
              onRetry={() => refetch()}
            />
          ) : isPremium ? (
            <SubnetBubbleChart
              subnets={displaySubnets}
              isLoading={isLoading}
              isError={isError}
              error={error}
              onRetry={() => refetch()}
            />
          ) : (
            <PremiumGate featureName="Bubble Chart">
              <SubnetBubbleChart
                subnets={displaySubnets}
                isLoading={isLoading}
              />
            </PremiumGate>
          )}
        </div>
      </div>
    </div>
  );
}

export default function ScreenerPage() {
  const queryClient = getQueryClient();

  return (
    <QueryClientProvider client={queryClient}>
      <ScreenerContent />
    </QueryClientProvider>
  );
}
