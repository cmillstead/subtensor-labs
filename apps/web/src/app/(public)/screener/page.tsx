"use client";

import { QueryClientProvider } from "@tanstack/react-query";
import { getQueryClient } from "@/lib/query-client";
import { LastUpdated } from "@/components/common/LastUpdated";
import { ScreenerTable } from "@/components/screener/ScreenerTable";
import { FilterPanel } from "@/components/screener/FilterPanel";
import { useScreener } from "@/hooks/useScreener";
import { useScreenerFilters } from "@/hooks/useScreenerFilters";

function ScreenerContent() {
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

  return (
    <div className="space-y-6">
      <header className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-text-primary">
            Subnet Screener
          </h1>
          <p className="mt-1 text-sm text-text-secondary">
            Browse and compare all active Bittensor subnets.
          </p>
        </div>
        {data?.meta?.last_updated && (
          <LastUpdated timestamp={data.meta.last_updated} />
        )}
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
          <ScreenerTable
            subnets={hasActiveFilters ? filteredSubnets : subnets}
            isLoading={isLoading}
            isError={isError}
            error={error}
            onRetry={() => refetch()}
          />
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
