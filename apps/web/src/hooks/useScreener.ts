"use client";

import { useQuery } from "@tanstack/react-query";
import type { EngineResponse, ScreenerResult } from "@/types";

async function fetchScreener(): Promise<EngineResponse<ScreenerResult>> {
  const response = await fetch("/api/proxy/screener/query");

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(
      body?.error?.message ?? `Screener request failed: ${response.status}`,
    );
  }

  return response.json();
}

export function useScreener() {
  return useQuery({
    queryKey: ["screener"],
    queryFn: fetchScreener,
    staleTime: 2 * 60 * 1000, // 2 minutes — matches backend cache TTL
    refetchOnWindowFocus: true,
    retry: 2,
  });
}
