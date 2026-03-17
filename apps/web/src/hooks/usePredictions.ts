"use client";

import { useQuery } from "@tanstack/react-query";
import type { EngineResponse, YieldProjectionResult, PredictionHorizon } from "@/types";

async function fetchYieldProjection(
  addresses: string[],
  horizons: PredictionHorizon[],
): Promise<EngineResponse<YieldProjectionResult>> {
  const response = await fetch("/api/predictions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      coldkey_addresses: addresses,
      horizons,
    }),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(
      body?.error?.message ?? `Prediction request failed: ${response.status}`,
    );
  }

  return response.json();
}

export function useYieldProjection(
  addresses: string[],
  horizons: PredictionHorizon[] = [30, 60, 90],
) {
  return useQuery({
    queryKey: ["predictions", "yield", ...addresses.toSorted(), ...horizons],
    queryFn: () => fetchYieldProjection(addresses, horizons),
    enabled: addresses.length > 0,
    staleTime: 60 * 60 * 1000, // 1 hour — matches backend Redis TTL
    refetchOnWindowFocus: false,
    retry: 2,
  });
}
