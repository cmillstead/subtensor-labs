"use client";

import { useState } from "react";
import { cn, truncateAddress } from "@/lib/utils";
import { TaoAmount } from "@/components/common/TaoAmount";
import type { SubnetPosition } from "@/types";

interface SubnetPositionCardProps {
  position: SubnetPosition;
  className?: string;
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function SubnetPositionSkeleton() {
  return (
    <div
      className="animate-pulse rounded-lg border border-border bg-surface p-5"
      aria-label="Loading subnet position"
    >
      <div className="mb-3 flex items-center justify-between">
        <div className="h-5 w-32 rounded bg-elevated" />
        <div className="h-4 w-16 rounded bg-elevated" />
      </div>
      <div className="space-y-2">
        <div className="h-4 w-40 rounded bg-elevated" />
        <div className="h-4 w-36 rounded bg-elevated" />
        <div className="h-4 w-28 rounded bg-elevated" />
      </div>
    </div>
  );
}

function SubnetPositionCard({ position, className }: SubnetPositionCardProps) {
  const [expanded, setExpanded] = useState(false);
  const totalValue = position.staked_tao + position.alpha_value_tao;
  const displayName = position.subnet_name ?? `SN${position.netuid}`;

  return (
    <div
      className={cn(
        "rounded-lg border border-border bg-surface transition-colors hover:border-border-hover",
        className,
      )}
      aria-label={`Position in subnet ${position.netuid} ${displayName} worth ${totalValue.toLocaleString("en-US", { minimumFractionDigits: 2 })} TAO`}
    >
      {/* Summary row — clickable to expand */}
      <button
        type="button"
        className="w-full p-5 text-left"
        onClick={() => setExpanded((prev) => !prev)}
        aria-expanded={expanded}
        data-state={expanded ? "open" : "closed"}
      >
        {/* Header: subnet name + emission badge */}
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-text-primary">
            SN{position.netuid}
            {position.subnet_name && (
              <span className="ml-1.5 text-text-secondary">
                · {position.subnet_name}
              </span>
            )}
          </h3>
          <div className="flex items-center gap-2">
            {position.is_miner && (
              <span className="rounded-full bg-accent/10 px-2 py-0.5 text-xs font-medium text-accent">
                Miner
              </span>
            )}
            {!position.is_active && (
              <span className="rounded-full bg-text-muted/10 px-2 py-0.5 text-xs font-medium text-text-muted">
                Inactive
              </span>
            )}
            <span
              className="font-mono text-xs text-text-secondary"
              aria-label={`${(position.emission_share * 100).toFixed(1)}% emission share`}
            >
              {(position.emission_share * 100).toFixed(1)}%
            </span>
          </div>
        </div>

        {/* Position metrics */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-xs text-text-secondary">Staked</span>
            <TaoAmount value={position.staked_tao} size="small" />
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-text-secondary">Alpha</span>
            <span className="font-mono text-sm text-text-primary">
              <span className="text-text-secondary">α</span>{" "}
              {position.alpha_holdings.toLocaleString("en-US", {
                minimumFractionDigits: 0,
                maximumFractionDigits: 2,
              })}
              <span className="ml-2 text-text-muted">
                (<TaoAmount value={position.alpha_value_tao} size="small" />)
              </span>
            </span>
          </div>
          {position.delegations.length > 0 &&
            position.delegations[0].estimated_apy != null && (
              <div className="flex items-center justify-between">
                <span className="text-xs text-text-secondary">Yield</span>
                <span className="font-mono text-sm text-text-primary">
                  {position.delegations[0].estimated_apy.toFixed(1)}% APY
                </span>
              </div>
            )}
        </div>
      </button>

      {/* Drill-down detail section */}
      <div
        className={cn(
          "grid transition-all duration-200 ease-in-out",
          expanded ? "grid-rows-[1fr]" : "grid-rows-[0fr]",
        )}
      >
        <div className="overflow-hidden">
          <div className="border-t border-border px-5 pb-5 pt-4">
            {/* Emission share */}
            <div className="mb-4 flex items-center justify-between text-sm">
              <span className="text-text-secondary">Emission Share</span>
              <span className="font-mono text-text-primary">
                {formatPercent(position.emission_share)}
              </span>
            </div>

            {/* Miner details */}
            {position.is_miner && (
              <div className="mb-4">
                <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-text-muted">
                  Miner Details
                </h4>
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-text-secondary">Incentive</span>
                    <span className="font-mono text-text-primary">
                      {formatPercent(position.incentive)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-text-secondary">Trust</span>
                    <span className="font-mono text-text-primary">
                      {formatPercent(position.trust)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-text-secondary">Dividends</span>
                    <TaoAmount value={position.dividends} size="small" />
                  </div>
                </div>
              </div>
            )}

            {/* Delegations table */}
            <div>
              <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-text-muted">
                Delegations
              </h4>
              {position.delegations.length === 0 ? (
                <p className="text-sm text-text-muted">
                  No delegation details available
                </p>
              ) : (
                <table className="w-full text-sm" aria-label="Delegation details">
                  <thead>
                    <tr className="border-b border-border text-left text-xs text-text-muted">
                      <th className="pb-1.5 font-medium">Validator</th>
                      <th className="pb-1.5 text-right font-medium">Amount</th>
                      <th className="pb-1.5 text-right font-medium">APY</th>
                      <th className="pb-1.5 text-right font-medium">Take</th>
                    </tr>
                  </thead>
                  <tbody>
                    {position.delegations.map((d) => (
                      <tr
                        key={d.validator_hotkey}
                        className="border-b border-border/50 last:border-0"
                      >
                        <td className="py-1.5">
                          <span className="text-text-primary">
                            {d.validator_name ?? truncateAddress(d.validator_hotkey)}
                          </span>
                        </td>
                        <td className="py-1.5 text-right">
                          <TaoAmount value={d.delegated_amount} size="small" />
                        </td>
                        <td className="py-1.5 text-right font-mono text-text-primary">
                          {d.estimated_apy != null
                            ? `${d.estimated_apy.toFixed(1)}%`
                            : "—"}
                        </td>
                        <td className="py-1.5 text-right font-mono text-text-primary">
                          {(d.take_rate * 100).toFixed(1)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export { SubnetPositionCard, SubnetPositionSkeleton };
