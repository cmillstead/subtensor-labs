"use client";

import { useMemo, useState } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { getQueryClient } from "@/lib/query-client";
import { PremiumGate } from "@/components/common/PremiumGate";
import {
  YieldProjector,
  YieldProjectorSkeleton,
} from "@/components/predictions/YieldProjector";
import {
  ScenarioCalculator,
  ScenarioCalculatorSkeleton,
} from "@/components/predictions/ScenarioCalculator";
import {
  EmissionForecaster,
  EmissionForecasterSkeleton,
} from "@/components/predictions/EmissionForecaster";
import { useYieldProjection, useEmissionForecast } from "@/hooks/usePredictions";
import { usePortfolio } from "@/hooks/usePortfolio";
import { useAddresses } from "@/hooks/useAddresses";
import { cn } from "@/lib/utils";

type PredictionTab = "yield" | "scenario" | "emission" | "alpha";

const TABS: { id: PredictionTab; label: string; enabled: boolean }[] = [
  { id: "yield", label: "Yield Projector", enabled: true },
  { id: "scenario", label: "Scenario Calculator", enabled: true },
  { id: "emission", label: "Emission Forecast", enabled: true },
  { id: "alpha", label: "Alpha Trends", enabled: false },
];

function PredictionsContent() {
  const [activeTab, setActiveTab] = useState<PredictionTab>("yield");
  const { addresses, hydrated } = useAddresses();

  const addressStrings = useMemo(
    () => addresses.map((a) => a.address),
    [addresses],
  );

  const { data, isLoading, isError, error } = useYieldProjection(addressStrings);
  const {
    data: emissionData,
    isLoading: emissionLoading,
    isError: emissionIsError,
    error: emissionError,
  } = useEmissionForecast(addressStrings);
  const { data: portfolioData } = usePortfolio(addressStrings);

  // Derive current stakes per subnet from portfolio positions
  const { currentStakes, availableNetuids } = useMemo(() => {
    const stakes: Record<number, number> = {};
    if (portfolioData?.data?.positions) {
      for (const pos of portfolioData.data.positions) {
        stakes[pos.netuid] = (stakes[pos.netuid] ?? 0) + pos.staked_tao;
      }
    }
    const netuids = Object.keys(stakes)
      .map(Number)
      .sort((a, b) => a - b);
    return { currentStakes: stakes, availableNetuids: netuids };
  }, [portfolioData]);

  const noAddresses = hydrated && addressStrings.length === 0;

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-text-primary">
          Predictions
        </h1>
        <p className="mt-1 text-sm text-text-secondary">
          Statistical projections for your Bittensor portfolio.
        </p>
      </header>

      {/* Tab navigation */}
      <div
        role="tablist"
        aria-label="Prediction tools"
        className="flex gap-1 border-b border-border"
      >
        {TABS.map((tab) => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={activeTab === tab.id}
            aria-disabled={!tab.enabled}
            disabled={!tab.enabled}
            onClick={() => tab.enabled && setActiveTab(tab.id)}
            className={cn(
              "relative px-4 py-2 text-sm font-medium transition-colors",
              activeTab === tab.id
                ? "text-violet-400"
                : tab.enabled
                  ? "text-text-secondary hover:text-text-primary"
                  : "cursor-not-allowed text-text-muted",
            )}
          >
            {tab.label}
            {!tab.enabled && (
              <span className="ml-1.5 rounded bg-elevated px-1.5 py-0.5 text-[10px] text-text-muted">
                Soon
              </span>
            )}
            {activeTab === tab.id && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-violet-400" />
            )}
          </button>
        ))}
      </div>

      {/* Yield Projector tab content */}
      {activeTab === "yield" && (
        <PremiumGate featureName="Yield Projector">
          {noAddresses ? (
            <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-border py-16 text-center">
              <p className="text-lg text-text-secondary">
                No addresses connected
              </p>
              <p className="mt-1 text-sm text-text-muted">
                Add coldkey addresses in your{" "}
                <a href="/dashboard" className="text-violet-400 underline">
                  Portfolio Dashboard
                </a>{" "}
                to see yield projections.
              </p>
            </div>
          ) : isLoading ? (
            <YieldProjectorSkeleton />
          ) : isError ? (
            <div
              className="rounded-lg border border-error/30 bg-error/5 p-4"
              role="alert"
            >
              <p className="text-sm text-error">
                {error?.message ?? "Failed to load predictions"}
              </p>
              <p className="mt-1 text-xs text-text-muted">
                Ensure your addresses have staking positions and try again.
              </p>
            </div>
          ) : data?.data ? (
            <YieldProjector
              chartData={data.data.chart_data}
              projections={data.data.projections}
              caveat={data.data.caveat}
              totalStakedTao={data.data.total_staked_tao}
              subnetsAnalyzed={data.data.subnets_analyzed}
              subnetsSkipped={data.data.subnets_skipped}
            />
          ) : null}
        </PremiumGate>
      )}

      {/* Scenario Calculator tab content */}
      {activeTab === "scenario" && (
        <PremiumGate featureName="Scenario Calculator">
          {noAddresses ? (
            <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-border py-16 text-center">
              <p className="text-lg text-text-secondary">
                No addresses connected
              </p>
              <p className="mt-1 text-sm text-text-muted">
                Add coldkey addresses in your{" "}
                <a href="/dashboard" className="text-violet-400 underline">
                  Portfolio Dashboard
                </a>{" "}
                to use the scenario calculator.
              </p>
            </div>
          ) : availableNetuids.length === 0 ? (
            <ScenarioCalculatorSkeleton />
          ) : (
            <ScenarioCalculator
              addresses={addressStrings}
              currentStakes={currentStakes}
              availableNetuids={availableNetuids}
            />
          )}
        </PremiumGate>
      )}

      {/* Emission Forecast tab content */}
      {activeTab === "emission" && (
        <PremiumGate featureName="Emission Forecast">
          {noAddresses ? (
            <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-border py-16 text-center">
              <p className="text-lg text-text-secondary">
                No addresses connected
              </p>
              <p className="mt-1 text-sm text-text-muted">
                Add coldkey addresses in your{" "}
                <a href="/dashboard" className="text-violet-400 underline">
                  Portfolio Dashboard
                </a>{" "}
                to view emission forecasts.
              </p>
            </div>
          ) : emissionLoading ? (
            <EmissionForecasterSkeleton />
          ) : emissionIsError ? (
            <div
              className="rounded-lg border border-error/30 bg-error/5 p-4"
              role="alert"
            >
              <p className="text-sm text-error">
                {emissionError?.message ?? "Failed to load emission forecast"}
              </p>
              <p className="mt-1 text-xs text-text-muted">
                Ensure your addresses have staking positions and try again.
              </p>
            </div>
          ) : emissionData?.data ? (
            <EmissionForecaster
              subnetForecasts={emissionData.data.subnet_forecasts}
              halvingImpact={emissionData.data.halving_impact}
              stakingMigration={emissionData.data.staking_migration}
              caveat={emissionData.data.caveat}
              subnetsAnalyzed={emissionData.data.subnets_analyzed}
              subnetsSkipped={emissionData.data.subnets_skipped}
            />
          ) : null}
        </PremiumGate>
      )}
    </div>
  );
}

export default function PredictionsPage() {
  const queryClient = getQueryClient();

  return (
    <QueryClientProvider client={queryClient}>
      <PredictionsContent />
    </QueryClientProvider>
  );
}
