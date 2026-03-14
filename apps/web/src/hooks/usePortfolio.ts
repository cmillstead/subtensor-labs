"use client";

import { useQuery } from "@tanstack/react-query";
import type { EngineResponse, PortfolioResult } from "@/types";

async function fetchPortfolio(
  addresses: string[],
): Promise<EngineResponse<PortfolioResult>> {
  const response = await fetch("/api/proxy/portfolio/aggregate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ coldkey_addresses: addresses }),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(
      body?.error?.message ?? `Portfolio request failed: ${response.status}`,
    );
  }

  return response.json();
}

export function usePortfolio(addresses: string[]) {
  return useQuery({
    queryKey: ["portfolio", ...addresses.toSorted()],
    queryFn: () => fetchPortfolio(addresses),
    enabled: addresses.length > 0,
    staleTime: 5 * 60 * 1000, // 5 minutes — matches backend cache TTL
    refetchOnWindowFocus: true,
    retry: 2,
  });
}
