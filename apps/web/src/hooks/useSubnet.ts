"use client";

import { useQuery } from "@tanstack/react-query";
import type { EngineResponse, SubnetDetailResult, TimeRange } from "@/types";

async function fetchSubnetDetail(
  netuid: number,
  timeRange: TimeRange,
): Promise<EngineResponse<SubnetDetailResult>> {
  const response = await fetch(
    `/api/proxy/subnets/${netuid}?time_range=${timeRange}`,
  );
  if (!response.ok) {
    throw new Error(`Failed to fetch subnet ${netuid}: ${response.status}`);
  }
  return response.json();
}

export function useSubnet(netuid: number, timeRange: TimeRange) {
  return useQuery({
    queryKey: ["subnet", netuid, timeRange],
    queryFn: () => fetchSubnetDetail(netuid, timeRange),
    staleTime: 2 * 60 * 1000,
  });
}
