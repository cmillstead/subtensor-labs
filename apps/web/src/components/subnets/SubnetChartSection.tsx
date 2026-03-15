"use client";

import { useState } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { getQueryClient } from "@/lib/query-client";
import { TimeRangeSelector } from "@/components/common/TimeRangeSelector";
import { SubnetChart } from "@/components/subnets/SubnetChart";
import { useSubnet } from "@/hooks/useSubnet";
import type { SubnetDetailResult, TimeRange } from "@/types";

function formatPercent(v: number): string {
  return `${(v * 100).toFixed(2)}%`;
}

function formatTao(v: number): string {
  if (v >= 1_000) return `${(v / 1_000).toFixed(1)}K`;
  return v.toFixed(4);
}

function formatInteger(v: number): string {
  return v.toLocaleString();
}

interface SubnetChartSectionInnerProps {
  initialData: SubnetDetailResult;
  netuid: number;
}

function SubnetChartSectionInner({
  initialData,
  netuid,
}: SubnetChartSectionInnerProps) {
  const [timeRange, setTimeRange] = useState<TimeRange>("30d");
  const isInitialRange = timeRange === "30d";
  const { data: response, isFetching } = useSubnet(netuid, timeRange);

  // Use SSR data for the initial 30d range until client fetch completes.
  // For other ranges, wait for client data (show SSR data as fallback while loading).
  const displayData = response?.data ?? initialData;

  return (
    <section>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xl font-semibold text-text-primary">
          Historical Charts
        </h2>
        <TimeRangeSelector value={timeRange} onChange={setTimeRange} />
      </div>
      <div className="grid gap-6 lg:grid-cols-3">
        <SubnetChart
          data={displayData.history}
          dataKey="emission_share"
          label="Emission Share"
          color="#8B5CF6"
          formatValue={formatPercent}
        />
        <SubnetChart
          data={displayData.history}
          dataKey="alpha_price"
          label="Alpha Price (τ)"
          color="#06B6D4"
          formatValue={formatTao}
        />
        <SubnetChart
          data={displayData.history}
          dataKey="miner_count"
          label="Miner Count"
          color="#10B981"
          formatValue={formatInteger}
        />
      </div>
    </section>
  );
}

interface SubnetChartSectionProps {
  initialData: SubnetDetailResult;
  netuid: number;
}

export function SubnetChartSection({
  initialData,
  netuid,
}: SubnetChartSectionProps) {
  const queryClient = getQueryClient();
  return (
    <QueryClientProvider client={queryClient}>
      <SubnetChartSectionInner initialData={initialData} netuid={netuid} />
    </QueryClientProvider>
  );
}
