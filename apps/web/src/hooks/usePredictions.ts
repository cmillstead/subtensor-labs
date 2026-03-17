"use client";

import { useQuery, useMutation } from "@tanstack/react-query";
import type { EngineResponse, YieldProjectionResult, PredictionHorizon, ScenarioCalcRequest, ScenarioComparisonResult, EmissionForecastResult } from "@/types";

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

export async function fetchScenarioCalculation(
  request: ScenarioCalcRequest,
): Promise<EngineResponse<ScenarioComparisonResult>> {
  const response = await fetch("/api/predictions/scenario", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(
      body?.error?.message ?? `Scenario calculation failed: ${response.status}`,
    );
  }

  return response.json();
}

export function useScenarioCalculation() {
  return useMutation({
    mutationFn: fetchScenarioCalculation,
  });
}

async function fetchEmissionForecast(
  addresses: string[],
): Promise<EngineResponse<EmissionForecastResult>> {
  const response = await fetch("/api/predictions/emission", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      coldkey_addresses: addresses,
    }),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(
      body?.error?.message ?? `Emission forecast request failed: ${response.status}`,
    );
  }

  return response.json();
}

export function useEmissionForecast(addresses: string[]) {
  return useQuery({
    queryKey: ["predictions", "emission", ...addresses.toSorted()],
    queryFn: () => fetchEmissionForecast(addresses),
    enabled: addresses.length > 0,
    staleTime: 60 * 60 * 1000, // 1 hour
    refetchOnWindowFocus: false,
    retry: 2,
  });
}
