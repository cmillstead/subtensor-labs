"use client";

import { useMemo, useState } from "react";
import {
  SubnetPositionCard,
  SubnetPositionSkeleton,
} from "@/components/portfolio/SubnetPositionCard";
import type { SubnetPosition } from "@/types";

type SortKey = "value" | "staked_tao" | "alpha_value_tao" | "emission_share" | "subnet_name";

const SORT_OPTIONS: { key: SortKey; label: string }[] = [
  { key: "value", label: "Total Value" },
  { key: "staked_tao", label: "Staked TAO" },
  { key: "alpha_value_tao", label: "Alpha Value" },
  { key: "emission_share", label: "Emission Share" },
  { key: "subnet_name", label: "Subnet Name" },
];

function sortPositions(
  positions: SubnetPosition[],
  sortKey: SortKey,
): SubnetPosition[] {
  return positions.toSorted((a, b) => {
    switch (sortKey) {
      case "value":
        return (b.staked_tao + b.alpha_value_tao) - (a.staked_tao + a.alpha_value_tao);
      case "staked_tao":
        return b.staked_tao - a.staked_tao;
      case "alpha_value_tao":
        return b.alpha_value_tao - a.alpha_value_tao;
      case "emission_share":
        return b.emission_share - a.emission_share;
      case "subnet_name": {
        const nameA = a.subnet_name ?? `SN${a.netuid}`;
        const nameB = b.subnet_name ?? `SN${b.netuid}`;
        return nameA.localeCompare(nameB);
      }
    }
  });
}

interface SubnetPositionListProps {
  positions: SubnetPosition[];
}

function SubnetPositionListSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 2xl:grid-cols-3">
      <SubnetPositionSkeleton />
      <SubnetPositionSkeleton />
      <SubnetPositionSkeleton />
    </div>
  );
}

function SubnetPositionList({ positions }: SubnetPositionListProps) {
  const [sortKey, setSortKey] = useState<SortKey>("value");

  const sorted = useMemo(
    () => sortPositions(positions, sortKey),
    [positions, sortKey],
  );

  if (positions.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-text-muted">
        No subnet positions found
      </p>
    );
  }

  return (
    <div>
      {/* Sort controls */}
      <div className="mb-4 flex items-center gap-2">
        <label
          htmlFor="position-sort"
          className="text-xs text-text-secondary"
        >
          Sort by
        </label>
        <select
          id="position-sort"
          value={sortKey}
          onChange={(e) => setSortKey(e.target.value as SortKey)}
          className="rounded border border-border bg-surface px-2 py-1 text-xs text-text-primary focus:outline-none focus:ring-1 focus:ring-accent"
        >
          {SORT_OPTIONS.map((opt) => (
            <option key={opt.key} value={opt.key}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Position cards grid */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 2xl:grid-cols-3">
        {sorted.map((pos) => (
          <SubnetPositionCard
            key={`${pos.netuid}:${pos.hotkey}`}
            position={pos}
          />
        ))}
      </div>
    </div>
  );
}

export { SubnetPositionList, SubnetPositionListSkeleton };
