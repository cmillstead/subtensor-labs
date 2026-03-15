"use client";

import { useQuery } from "@tanstack/react-query";
import type {
  EngineResponse,
  PortfolioHistoryResult,
  TimeRange,
} from "@/types";

async function fetchPortfolioHistory(
  addresses: string[],
  timeRange: TimeRange,
): Promise<EngineResponse<PortfolioHistoryResult>> {
  const response = await fetch("/api/proxy/portfolio/history", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      coldkey_addresses: addresses,
      time_range: timeRange,
    }),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(
      body?.error?.message ??
        `Portfolio history request failed: ${response.status}`,
    );
  }

  return response.json();
}

export function usePortfolioHistory(
  addresses: string[],
  timeRange: TimeRange,
) {
  return useQuery({
    queryKey: ["portfolio-history", ...addresses.toSorted(), timeRange],
    queryFn: () => fetchPortfolioHistory(addresses, timeRange),
    enabled: addresses.length > 0,
    staleTime: 5 * 60 * 1000,
    refetchOnWindowFocus: true,
    retry: 2,
  });
}
