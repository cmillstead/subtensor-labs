"use client";

import { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// Page title set via companion layout.tsx (Client Components cannot export metadata)
import { AddressManager } from "@/components/portfolio/AddressManager";
import {
  PortfolioSummary,
  PortfolioSkeleton,
} from "@/components/portfolio/PortfolioSummary";
import { usePortfolio } from "@/hooks/usePortfolio";

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
  const [addresses, setAddresses] = useState<string[]>([]);
  const { data, isLoading, isError, error } = usePortfolio(addresses);

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
        addresses={addresses}
        onAddressesChange={setAddresses}
      />

      {addresses.length === 0 && (
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-border py-16 text-center">
          <p className="text-lg text-text-secondary">No addresses added</p>
          <p className="mt-1 text-sm text-text-muted">
            Paste a coldkey address above to see your portfolio summary.
          </p>
        </div>
      )}

      {isLoading && <PortfolioSkeleton />}

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
        <PortfolioSummary
          portfolio={data.data}
          change24h={data.data.change_24h_pct}
          change7d={data.data.change_7d_pct}
        />
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
