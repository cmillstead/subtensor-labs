"use client";

import { useState, useCallback } from "react";
import { useSession } from "next-auth/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { getQueryClient } from "@/lib/query-client";
import { LastUpdated } from "@/components/common/LastUpdated";
import { PremiumGate } from "@/components/common/PremiumGate";
import { ScreenerTable } from "@/components/screener/ScreenerTable";
import { FilterPanel } from "@/components/screener/FilterPanel";
import { ScreenerCSVExport } from "@/components/screener/ScreenerCSVExport";
import { SubnetBubbleChart } from "@/components/screener/SubnetBubbleChart";
import { SubnetCompare } from "@/components/screener/SubnetCompare";
import { ViewToggle } from "@/components/screener/ViewToggle";
import type { ScreenerView } from "@/components/screener/ViewToggle";
import { useScreener } from "@/hooks/useScreener";
import { useScreenerFilters } from "@/hooks/useScreenerFilters";
import { Button } from "@/components/ui/button";

function ScreenerContent() {
  const { data: session } = useSession();
  const isPremium = session?.user?.premiumStatus === "premium";
  const [view, setView] = useState<ScreenerView>("table");
  const [selectedNetuids, setSelectedNetuids] = useState<Set<number>>(new Set());
  const [showCompare, setShowCompare] = useState(false);

  const handleCompare = useCallback(() => {
    setShowCompare(true);
  }, []);

  const handleCloseCompare = useCallback(() => {
    setShowCompare(false);
  }, []);

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

  // Count selected netuids that are actually visible in current display set
  const visibleSelectedCount = displaySubnets
    ? displaySubnets.filter((s) => selectedNetuids.has(s.netuid)).length
    : 0;
  const canCompare = visibleSelectedCount >= 2 && visibleSelectedCount <= 3;

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

      {showCompare && displaySubnets ? (
        <SubnetCompare
          subnets={displaySubnets.filter((s) => selectedNetuids.has(s.netuid))}
          onClose={handleCloseCompare}
        />
      ) : (
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
              <>
                <ScreenerTable
                  subnets={displaySubnets}
                  isLoading={isLoading}
                  isError={isError}
                  error={error}
                  onRetry={() => refetch()}
                  selectedNetuids={selectedNetuids}
                  onSelectionChange={setSelectedNetuids}
                />
                {canCompare && (
                  <div className="fixed bottom-6 left-1/2 z-50 -translate-x-1/2">
                    <Button
                      variant="outline"
                      className="border-violet-500 text-violet-400 hover:bg-violet-500/10"
                      onClick={handleCompare}
                    >
                      Compare ({visibleSelectedCount})
                    </Button>
                  </div>
                )}
              </>
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
      )}
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
