"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { cn } from "@/lib/utils";
import { formatTao } from "@/components/common/TaoAmount";
import { TrendBadge } from "@/components/common/TrendBadge";
import { useScenarioCalculation } from "@/hooks/usePredictions";
import type {
  PredictionHorizon,
  ScenarioInput,
  ScenarioMove,
  ScenarioOutcome,
  ScenarioComparisonResult,
  SubnetAllocation,
} from "@/types";

// Scenario color palette
const SCENARIO_COLORS = {
  baseline: "#8B5CF6", // Violet
  scenarios: ["#F43F5E", "#10B981", "#F59E0B"] as const, // Rose, Emerald, Amber
  grid: "#27272A",
  axisText: "#A1A1AA",
} as const;

const HORIZONS: { value: PredictionHorizon; label: string }[] = [
  { value: 30, label: "30D" },
  { value: 60, label: "60D" },
  { value: 90, label: "90D" },
];

const MAX_SCENARIOS = 3;

let _nextId = 1;
function nextId(): string {
  return String(_nextId++);
}

/** ScenarioInput with a stable unique ID for React keys */
interface IdentifiedScenarioInput extends ScenarioInput {
  _id: string;
  moves: IdentifiedScenarioMove[];
}

interface IdentifiedScenarioMove extends ScenarioMove {
  _id: string;
}

function makeMove(source: number, dest: number, amount = 0): IdentifiedScenarioMove {
  return { _id: nextId(), source_netuid: source, dest_netuid: dest, amount_tao: amount };
}

function makeScenario(source: number, dest: number): IdentifiedScenarioInput {
  return { _id: nextId(), label: null, moves: [makeMove(source, dest)] };
}

// --- Pure data-transform functions (exported for testing) ---

/** Compute allocation bar chart data from a comparison result */
export function buildComparisonChartData(
  comparison: ScenarioComparisonResult,
): { name: string; yield: number; color: string }[] {
  const items = [
    {
      name: "Current",
      yield: comparison.baseline.total_projected_yield_tao,
      color: SCENARIO_COLORS.baseline,
    },
  ];
  comparison.scenarios.forEach((s, i) => {
    items.push({
      name: s.label ?? `Scenario ${i + 1}`,
      yield: s.total_projected_yield_tao,
      color: SCENARIO_COLORS.scenarios[i % SCENARIO_COLORS.scenarios.length],
    });
  });
  return items;
}

/** Determine which scenario is best for yield / diversification */
export function getBestLabels(comparison: ScenarioComparisonResult): {
  bestYield: string | null;
  bestDiversification: string | null;
} {
  const { scenarios, best_yield_index, best_diversification_index } = comparison;
  return {
    bestYield: scenarios[best_yield_index]?.label ?? null,
    bestDiversification: scenarios[best_diversification_index]?.label ?? null,
  };
}

// --- Internal components ---

interface HorizonSelectorProps {
  value: PredictionHorizon;
  onChange: (h: PredictionHorizon) => void;
}

function HorizonSelector({ value, onChange }: HorizonSelectorProps) {
  return (
    <div
      role="radiogroup"
      aria-label="Projection horizon"
      className="inline-flex rounded-lg bg-elevated p-0.5"
    >
      {HORIZONS.map((h) => (
        <button
          key={h.value}
          role="radio"
          aria-checked={value === h.value}
          onClick={() => onChange(h.value)}
          className={cn(
            "rounded-md px-3 py-1 text-xs font-medium font-mono transition-colors",
            value === h.value
              ? "bg-accent text-white"
              : "text-text-secondary hover:text-text-primary",
          )}
        >
          {h.label}
        </button>
      ))}
    </div>
  );
}

interface MoveBuilderProps {
  move: ScenarioMove;
  availableNetuids: number[];
  onUpdate: (move: ScenarioMove) => void;
  onRemove: () => void;
  maxAmount: number;
}

function MoveBuilder({
  move,
  availableNetuids,
  onUpdate,
  onRemove,
  maxAmount,
}: MoveBuilderProps) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <label className="flex items-center gap-1.5 text-sm text-text-secondary">
        From
        <select
          value={move.source_netuid}
          onChange={(e) =>
            onUpdate({ ...move, source_netuid: Number(e.target.value) })
          }
          className="rounded border border-border bg-surface px-2 py-1 font-mono text-sm text-text-primary"
          aria-label="Source subnet"
        >
          {availableNetuids.map((n) => (
            <option key={n} value={n}>
              SN{n}
            </option>
          ))}
        </select>
      </label>

      <span className="text-text-muted">→</span>

      <label className="flex items-center gap-1.5 text-sm text-text-secondary">
        To
        <select
          value={move.dest_netuid}
          onChange={(e) =>
            onUpdate({ ...move, dest_netuid: Number(e.target.value) })
          }
          className="rounded border border-border bg-surface px-2 py-1 font-mono text-sm text-text-primary"
          aria-label="Destination subnet"
        >
          {availableNetuids.map((n) => (
            <option key={n} value={n}>
              SN{n}
            </option>
          ))}
        </select>
      </label>

      <label className="flex flex-1 items-center gap-2 text-sm text-text-secondary">
        <input
          type="range"
          min={0}
          max={Math.max(maxAmount, 1)}
          step={1}
          value={move.amount_tao}
          onChange={(e) =>
            onUpdate({ ...move, amount_tao: Number(e.target.value) })
          }
          className="h-1.5 flex-1 cursor-pointer appearance-none rounded-full bg-elevated accent-violet-500"
          aria-label="TAO amount to move"
        />
        <span className="w-20 text-right font-mono text-sm text-text-primary">
          τ {formatTao(move.amount_tao, true)}
        </span>
      </label>

      <button
        onClick={onRemove}
        className="rounded p-1 text-text-muted hover:bg-elevated hover:text-error"
        aria-label="Remove move"
      >
        ✕
      </button>
    </div>
  );
}

interface ScenarioCardProps {
  index: number;
  scenario: ScenarioInput;
  availableNetuids: number[];
  stakes: Record<number, number>;
  onUpdate: (scenario: ScenarioInput) => void;
  onRemove: () => void;
}

function ScenarioCard({
  index,
  scenario,
  availableNetuids,
  stakes,
  onUpdate,
  onRemove,
}: ScenarioCardProps) {
  const color = SCENARIO_COLORS.scenarios[index % SCENARIO_COLORS.scenarios.length];

  const addMove = () => {
    const first = availableNetuids[0] ?? 1;
    const second = availableNetuids[1] ?? availableNetuids[0] ?? 2;
    onUpdate({
      ...scenario,
      moves: [...scenario.moves, makeMove(first, second)],
    });
  };

  return (
    <div
      className="rounded-lg border border-border bg-surface p-4"
      style={{ borderLeftColor: color, borderLeftWidth: 3 }}
    >
      <div className="mb-3 flex items-center justify-between">
        <input
          type="text"
          value={scenario.label ?? ""}
          onChange={(e) => onUpdate({ ...scenario, label: e.target.value || null })}
          placeholder={`Scenario ${index + 1}`}
          className="bg-transparent text-sm font-semibold text-text-primary placeholder-text-muted outline-none"
          aria-label={`Scenario ${index + 1} name`}
        />
        <button
          onClick={onRemove}
          className="rounded px-2 py-0.5 text-xs text-text-muted hover:bg-elevated hover:text-error"
          aria-label={`Remove scenario ${index + 1}`}
        >
          Remove
        </button>
      </div>

      <div className="space-y-2">
        {scenario.moves.map((move, mi) => (
          <MoveBuilder
            key={(move as IdentifiedScenarioMove)._id ?? mi}
            move={move}
            availableNetuids={availableNetuids}
            maxAmount={stakes[move.source_netuid] ?? 0}
            onUpdate={(updated) => {
              const newMoves = [...scenario.moves];
              newMoves[mi] = updated;
              onUpdate({ ...scenario, moves: newMoves });
            }}
            onRemove={() => {
              onUpdate({
                ...scenario,
                moves: scenario.moves.filter((_, j) => j !== mi),
              });
            }}
          />
        ))}
      </div>

      {scenario.moves.length < 10 && (
        <button
          onClick={addMove}
          className="mt-2 text-xs text-violet-400 hover:text-violet-300"
        >
          + Add move
        </button>
      )}
    </div>
  );
}

interface OutcomeCardProps {
  outcome: ScenarioOutcome;
  color: string;
  isBestYield: boolean;
  isBestDiv: boolean;
}

function OutcomeCard({ outcome, color, isBestYield, isBestDiv }: OutcomeCardProps) {
  return (
    <div
      className="flex-1 rounded-lg border border-border bg-surface p-4"
      style={{ borderTopColor: color, borderTopWidth: 3 }}
    >
      <h4 className="mb-3 text-sm font-semibold text-text-primary">
        {outcome.label ?? "Scenario"}
      </h4>

      <div className="space-y-2">
        <div>
          <p className="text-xs text-text-secondary">Projected Yield</p>
          <p className="font-mono text-lg font-semibold text-text-primary">
            τ {formatTao(outcome.total_projected_yield_tao, true)}
          </p>
          {outcome.yield_delta_tao !== 0 && (
            <TrendBadge value={outcome.yield_delta_pct} className="text-xs" />
          )}
        </div>

        <div>
          <p className="text-xs text-text-secondary">68% Range</p>
          <p className="font-mono text-sm text-text-secondary">
            τ {formatTao(outcome.total_confidence_68_lower, true)} –{" "}
            {formatTao(outcome.total_confidence_68_upper, true)}
          </p>
        </div>

        <div>
          <p className="text-xs text-text-secondary">Alpha Exposure</p>
          <p className="font-mono text-sm text-text-secondary">
            τ {formatTao(outcome.total_alpha_exposure_tao, true)}
          </p>
        </div>

        <div>
          <p className="text-xs text-text-secondary">Diversification (HHI)</p>
          <p className="font-mono text-sm text-text-secondary">
            {outcome.hhi.toFixed(0)}
          </p>
        </div>
      </div>

      {(isBestYield || isBestDiv) && (
        <div className="mt-3 flex flex-wrap gap-1">
          {isBestYield && (
            <span className="rounded bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-400">
              Best Yield
            </span>
          )}
          {isBestDiv && (
            <span className="rounded bg-blue-500/10 px-2 py-0.5 text-[10px] font-medium text-blue-400">
              Best Diversification
            </span>
          )}
        </div>
      )}
    </div>
  );
}

interface ComparisonChartProps {
  data: { name: string; yield: number; color: string }[];
}

function ComparisonChart({ data }: ComparisonChartProps) {
  return (
    <div
      role="img"
      aria-label="Scenario yield comparison bar chart"
    >
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={data} margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={SCENARIO_COLORS.grid} />
          <XAxis
            dataKey="name"
            tick={{ fill: SCENARIO_COLORS.axisText, fontSize: 12 }}
          />
          <YAxis
            tick={{ fill: SCENARIO_COLORS.axisText, fontSize: 12 }}
            tickFormatter={(v: number) => `τ${v.toFixed(1)}`}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "#18181B",
              border: "1px solid #27272A",
              borderRadius: 8,
            }}
            labelStyle={{ color: "#A1A1AA" }}
            formatter={(value: number) => [`τ ${formatTao(value, true)}`, "Yield"]}
          />
          <Bar dataKey="yield" radius={[4, 4, 0, 0]}>
            {data.map((entry, i) => (
              <Cell key={i} fill={entry.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// --- Main component ---

interface ScenarioCalculatorProps {
  addresses: string[];
  currentStakes: Record<number, number>;
  availableNetuids: number[];
}

function ScenarioCalculator({
  addresses,
  currentStakes,
  availableNetuids,
}: ScenarioCalculatorProps) {
  const [horizon, setHorizon] = useState<PredictionHorizon>(90);
  const firstNetuid = availableNetuids[0] ?? 1;
  const secondNetuid = availableNetuids[1] ?? availableNetuids[0] ?? 2;
  const [scenarios, setScenarios] = useState<IdentifiedScenarioInput[]>([
    makeScenario(firstNetuid, secondNetuid),
  ]);

  const { mutate, isPending, isError, error, data } = useScenarioCalculation();
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(null);

  const debouncedCalculate = useCallback(
    (currentScenarios: IdentifiedScenarioInput[], currentHorizon: PredictionHorizon) => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => {
        const validScenarios = currentScenarios.filter(
          (s) => s.moves.length > 0 && s.moves.some((m) => m.amount_tao > 0),
        );
        if (validScenarios.length === 0 || addresses.length === 0) return;

        mutate({
          coldkey_addresses: addresses,
          scenarios: validScenarios.map((s) => ({
            label: s.label,
            moves: s.moves.map((m) => ({
              source_netuid: m.source_netuid,
              dest_netuid: m.dest_netuid,
              amount_tao: m.amount_tao,
            })),
          })),
          horizon: currentHorizon,
        });
      }, 300);
    },
    [addresses, mutate],
  );

  // Auto-calculate when scenarios or horizon change (AC2: real-time updates)
  useEffect(() => {
    debouncedCalculate(scenarios, horizon);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [scenarios, horizon, debouncedCalculate]);

  const addScenario = () => {
    if (scenarios.length >= MAX_SCENARIOS) return;
    setScenarios([...scenarios, makeScenario(firstNetuid, secondNetuid)]);
  };

  const comparison = data?.data;
  const chartData = comparison ? buildComparisonChartData(comparison) : null;
  const bestLabels = comparison ? getBestLabels(comparison) : null;

  return (
    <div className="space-y-6">
      {/* Caveat banner */}
      <div
        className="rounded-lg border border-amber-500/30 bg-amber-500/5 px-4 py-3"
        role="alert"
      >
        <p className="text-sm text-amber-200">
          Based on trend extrapolation. Not financial advice. Past emission
          trends do not guarantee future results.
        </p>
      </div>

      {/* Current allocation summary */}
      <section className="rounded-lg border border-border bg-surface p-5">
        <h2 className="mb-3 text-lg font-semibold text-text-primary">
          Current Allocation
        </h2>
        <div className="flex flex-wrap gap-3">
          {Object.entries(currentStakes)
            .filter(([, stake]) => stake > 0)
            .sort(([, a], [, b]) => b - a)
            .map(([netuid, stake]) => (
              <div
                key={netuid}
                className="rounded border border-border bg-elevated px-3 py-2"
              >
                <p className="text-xs text-text-secondary">SN{netuid}</p>
                <p className="font-mono text-sm font-medium text-text-primary">
                  τ {formatTao(stake, true)}
                </p>
              </div>
            ))}
        </div>
        <p className="mt-2 font-mono text-sm text-text-secondary">
          Total: τ{" "}
          {formatTao(
            Object.values(currentStakes).reduce((a, b) => a + b, 0),
            true,
          )}
        </p>
      </section>

      {/* Scenario builder */}
      <section className="rounded-lg border border-border bg-surface p-5">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-text-primary">Scenarios</h2>
          <HorizonSelector value={horizon} onChange={setHorizon} />
        </div>

        <div className="space-y-4">
          {scenarios.map((scenario, i) => (
            <ScenarioCard
              key={scenario._id}
              index={i}
              scenario={scenario}
              availableNetuids={availableNetuids}
              stakes={currentStakes}
              onUpdate={(updated) => {
                const next = [...scenarios];
                next[i] = updated as IdentifiedScenarioInput;
                setScenarios(next);
              }}
              onRemove={() => {
                setScenarios(scenarios.filter((s) => s._id !== scenario._id));
              }}
            />
          ))}
        </div>

        <div className="mt-4 flex items-center gap-3">
          {scenarios.length < MAX_SCENARIOS && (
            <button
              onClick={addScenario}
              className="rounded-lg border border-dashed border-border px-4 py-2 text-sm text-violet-400 hover:border-violet-400 hover:bg-violet-400/5"
            >
              + Add Scenario
            </button>
          )}

          <button
            onClick={() => debouncedCalculate(scenarios, horizon)}
            disabled={isPending || addresses.length === 0}
            className={cn(
              "rounded-lg px-6 py-2 text-sm font-medium transition-colors",
              isPending
                ? "cursor-wait bg-elevated text-text-muted"
                : "bg-violet-600 text-white hover:bg-violet-500",
            )}
          >
            {isPending ? "Calculating..." : "Calculate"}
          </button>
        </div>
      </section>

      {/* Error state */}
      {isError && (
        <div
          className="rounded-lg border border-error/30 bg-error/5 p-4"
          role="alert"
        >
          <p className="text-sm text-error">
            {error?.message ?? "Scenario calculation failed"}
          </p>
        </div>
      )}

      {/* Comparison results */}
      {comparison && (
        <section className="space-y-6">
          {/* Yield comparison chart */}
          {chartData && (
            <div className="rounded-lg border border-border bg-surface p-5">
              <h2 className="mb-3 text-lg font-semibold text-text-primary">
                Yield Comparison ({comparison.horizon_days}d)
              </h2>
              <ComparisonChart data={chartData} />
            </div>
          )}

          {/* Side-by-side outcome cards */}
          <div className="rounded-lg border border-border bg-surface p-5">
            <h2 className="mb-4 text-lg font-semibold text-text-primary">
              Side-by-Side Comparison
            </h2>
            <div className="flex flex-col gap-4 lg:flex-row">
              <OutcomeCard
                outcome={comparison.baseline}
                color={SCENARIO_COLORS.baseline}
                isBestYield={false}
                isBestDiv={false}
              />
              {comparison.scenarios.map((s, i) => (
                <OutcomeCard
                  key={i}
                  outcome={s}
                  color={
                    SCENARIO_COLORS.scenarios[
                      i % SCENARIO_COLORS.scenarios.length
                    ]
                  }
                  isBestYield={i === comparison.best_yield_index}
                  isBestDiv={i === comparison.best_diversification_index}
                />
              ))}
            </div>
          </div>

          {/* Summary highlights */}
          {bestLabels && (
            <div className="flex flex-wrap gap-3">
              {bestLabels.bestYield && (
                <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/5 px-4 py-2">
                  <span className="text-xs text-text-secondary">
                    Highest Projected Yield:
                  </span>{" "}
                  <span className="text-sm font-medium text-emerald-400">
                    {bestLabels.bestYield}
                  </span>
                </div>
              )}
              {bestLabels.bestDiversification && (
                <div className="rounded-lg border border-blue-500/30 bg-blue-500/5 px-4 py-2">
                  <span className="text-xs text-text-secondary">
                    Best Diversification:
                  </span>{" "}
                  <span className="text-sm font-medium text-blue-400">
                    {bestLabels.bestDiversification}
                  </span>
                </div>
              )}
            </div>
          )}
        </section>
      )}
    </div>
  );
}

function ScenarioCalculatorSkeleton() {
  return (
    <div className="space-y-6" aria-label="Loading scenario calculator">
      {/* Caveat skeleton */}
      <div className="h-12 animate-pulse rounded-lg bg-elevated" />

      {/* Allocation skeleton */}
      <div className="rounded-lg border border-border bg-surface p-5">
        <div className="mb-3 h-5 w-36 animate-pulse rounded bg-elevated" />
        <div className="flex gap-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-14 w-24 animate-pulse rounded bg-elevated" />
          ))}
        </div>
      </div>

      {/* Scenario builder skeleton */}
      <div className="rounded-lg border border-border bg-surface p-5">
        <div className="mb-4 flex items-center justify-between">
          <div className="h-5 w-24 animate-pulse rounded bg-elevated" />
          <div className="h-7 w-28 animate-pulse rounded bg-elevated" />
        </div>
        <div className="h-24 animate-pulse rounded bg-elevated" />
        <div className="mt-4 flex gap-3">
          <div className="h-9 w-32 animate-pulse rounded bg-elevated" />
          <div className="h-9 w-28 animate-pulse rounded bg-elevated" />
        </div>
      </div>
    </div>
  );
}

export { ScenarioCalculator, ScenarioCalculatorSkeleton };
