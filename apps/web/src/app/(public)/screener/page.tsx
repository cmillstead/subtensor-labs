"use client";

import { QueryClientProvider } from "@tanstack/react-query";
import { getQueryClient } from "@/lib/query-client";
import { LastUpdated } from "@/components/common/LastUpdated";
import { ScreenerTable } from "@/components/screener/ScreenerTable";
import { useScreener } from "@/hooks/useScreener";

function ScreenerContent() {
  const { data, isLoading, isError, error, refetch } = useScreener();

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

      {data?.data?.subnet_count !== undefined && (
        <p className="text-sm text-text-secondary">
          Showing {data.data.subnet_count} {data.data.subnet_count === 1 ? "subnet" : "subnets"}
        </p>
      )}

      <ScreenerTable
        subnets={data?.data?.subnets}
        isLoading={isLoading}
        isError={isError}
        error={error}
        onRetry={() => refetch()}
      />
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
