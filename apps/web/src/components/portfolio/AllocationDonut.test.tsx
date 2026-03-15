import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import {
  AllocationDonut,
  AllocationDonutSkeleton,
  computeAllocationData,
} from "./AllocationDonut";
import type { SubnetPosition } from "@/types";

// Mock ResizeObserver for Recharts ResponsiveContainer
class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = ResizeObserverMock;

function makePosition(
  netuid: number,
  staked_tao: number,
  alpha_value_tao: number,
  subnet_name: string | null = null,
): SubnetPosition {
  return {
    netuid,
    subnet_name,
    hotkey: `5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty`,
    staked_tao,
    alpha_holdings: 0,
    alpha_value_tao,
    emission_share: 0,
    incentive: 0,
    trust: 0,
    dividends: 0,
    is_active: true,
    is_miner: false,
    delegations: [],
  };
}

describe("computeAllocationData", () => {
  it("returns empty array for empty positions", () => {
    expect(computeAllocationData([], 0)).toEqual([]);
  });

  it("returns empty array when totalValueTao is zero", () => {
    const positions = [makePosition(1, 100, 50)];
    expect(computeAllocationData(positions, 0)).toEqual([]);
  });

  it("computes correct slices for 3 positions", () => {
    const positions = [
      makePosition(1, 100, 50, "Alpha"),
      makePosition(2, 200, 100, "Beta"),
      makePosition(3, 50, 25, "Gamma"),
    ];
    const total = 525; // 150 + 300 + 75
    const slices = computeAllocationData(positions, total);

    expect(slices).toHaveLength(3);
    // Sorted by value desc
    expect(slices[0].name).toBe("Beta");
    expect(slices[0].value).toBeCloseTo(300);
    expect(slices[1].name).toBe("Alpha");
    expect(slices[1].value).toBeCloseTo(150);
    expect(slices[2].name).toBe("Gamma");
    expect(slices[2].value).toBeCloseTo(75);
  });

  it("groups into Other when more than 8 subnets", () => {
    const positions = Array.from({ length: 10 }, (_, i) =>
      makePosition(i + 1, 100 - i * 5, 50 - i * 2, `Subnet${i + 1}`),
    );
    const total = positions.reduce(
      (sum, p) => sum + p.staked_tao + p.alpha_value_tao,
      0,
    );
    const slices = computeAllocationData(positions, total);

    expect(slices).toHaveLength(9); // 8 named + 1 Other
    expect(slices[8].name).toBe("Other");
    expect(slices[8].isOther).toBe(true);
    expect(slices[8].children).toHaveLength(2);
  });

  it("computes percentages that sum to approximately 100%", () => {
    const positions = [
      makePosition(1, 100, 0),
      makePosition(2, 200, 0),
      makePosition(3, 300, 0),
    ];
    const total = 600;
    const slices = computeAllocationData(positions, total);
    const sum = slices.reduce((s, slice) => s + slice.percentage, 0);
    expect(sum).toBeCloseTo(100, 0);
  });

  it("uses SN{netuid} fallback when subnet_name is null", () => {
    const positions = [makePosition(42, 100, 50, null)];
    const slices = computeAllocationData(positions, 150);
    expect(slices[0].name).toBe("SN42");
  });

  it("aggregates multiple positions for same netuid", () => {
    const positions = [
      makePosition(1, 100, 50, "Alpha"),
      makePosition(1, 200, 100, "Alpha"),
    ];
    const slices = computeAllocationData(positions, 450);
    expect(slices).toHaveLength(1);
    expect(slices[0].value).toBeCloseTo(450);
  });
});

describe("AllocationDonut", () => {
  it("renders nothing when positions is empty", () => {
    const { container } = render(
      <AllocationDonut positions={[]} totalValueTao={0} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders chart container with correct aria-label", () => {
    const positions = [makePosition(1, 100, 50, "Alpha")];
    render(
      <AllocationDonut positions={positions} totalValueTao={150} />,
    );
    expect(
      screen.getByLabelText(
        "Portfolio allocation chart showing subnet exposure percentages",
      ),
    ).toBeInTheDocument();
  });

  it("renders legend with subnet names and percentages", () => {
    const positions = [
      makePosition(1, 100, 50, "Alpha"),
      makePosition(2, 200, 100, "Beta"),
    ];
    render(
      <AllocationDonut positions={positions} totalValueTao={450} />,
    );

    expect(screen.getByText("Alpha")).toBeInTheDocument();
    expect(screen.getByText("Beta")).toBeInTheDocument();
    // Percentages: Beta = 300/450 = 66.7%, Alpha = 150/450 = 33.3%
    expect(screen.getByText("66.7%")).toBeInTheDocument();
    expect(screen.getByText("33.3%")).toBeInTheDocument();
  });

  it("renders 'Other' in legend when more than 8 subnets", () => {
    const positions = Array.from({ length: 10 }, (_, i) =>
      makePosition(i + 1, 100 - i * 5, 50 - i * 2, `Subnet${i + 1}`),
    );
    const total = positions.reduce(
      (sum, p) => sum + p.staked_tao + p.alpha_value_tao,
      0,
    );
    render(
      <AllocationDonut positions={positions} totalValueTao={total} />,
    );

    expect(screen.getByText("Other")).toBeInTheDocument();
    // First 8 should be named
    expect(screen.getByText("Subnet1")).toBeInTheDocument();
    expect(screen.getByText("Subnet8")).toBeInTheDocument();
  });

  it("calls onSliceClick with netuid when legend item clicked", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    const positions = [
      makePosition(1, 100, 50, "Alpha"),
      makePosition(2, 200, 100, "Beta"),
    ];
    render(
      <AllocationDonut
        positions={positions}
        totalValueTao={450}
        onSliceClick={onClick}
      />,
    );

    await user.click(screen.getByText("Alpha"));
    expect(onClick).toHaveBeenCalledWith(1);
  });

  it("renders total value in center (thousands)", () => {
    const positions = [makePosition(1, 2500, 500, "Alpha")];
    render(
      <AllocationDonut positions={positions} totalValueTao={3000} />,
    );

    // 3000 → "3.0K"
    expect(screen.getByText("3.0K")).toBeInTheDocument();
    expect(screen.getByText("Total")).toBeInTheDocument();
  });

  it("renders total value in center (millions)", () => {
    const positions = [makePosition(1, 1_500_000, 500_000, "Alpha")];
    render(
      <AllocationDonut positions={positions} totalValueTao={2_000_000} />,
    );

    // 2,000,000 → "2.0M"
    expect(screen.getByText("2.0M")).toBeInTheDocument();
  });
});

describe("AllocationDonutSkeleton", () => {
  it("renders skeleton with loading label", () => {
    render(<AllocationDonutSkeleton />);
    expect(
      screen.getByLabelText("Loading allocation chart"),
    ).toBeInTheDocument();
  });
});
