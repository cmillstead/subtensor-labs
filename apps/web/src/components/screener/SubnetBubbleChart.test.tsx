import React from "react";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  SubnetBubbleChart,
  SubnetBubbleChartSkeleton,
  prepareBubbleData,
} from "./SubnetBubbleChart";
import type { ScreenerSubnet } from "@/types";

// Mock ResizeObserver for Recharts ResponsiveContainer
class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = ResizeObserverMock;

// Mock next/navigation
const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

// Mock recharts to render testable elements
vi.mock("recharts", () => ({
  ScatterChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="scatter-chart">{children}</div>
  ),
  Scatter: (props: { data: unknown[] }) => (
    <div data-testid="scatter" data-count={props.data?.length ?? 0} />
  ),
  XAxis: (props: { name: string }) => (
    <div data-testid="x-axis" data-name={props.name} />
  ),
  YAxis: (props: { name: string }) => (
    <div data-testid="y-axis" data-name={props.name} />
  ),
  ZAxis: (props: { range: number[] }) => (
    <div
      data-testid="z-axis"
      data-range-min={props.range?.[0]}
      data-range-max={props.range?.[1]}
    />
  ),
  CartesianGrid: () => <div data-testid="cartesian-grid" />,
  Tooltip: () => <div data-testid="tooltip" />,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
}));

function makeSubnet(overrides: Partial<ScreenerSubnet> = {}): ScreenerSubnet {
  return {
    netuid: 1,
    name: "Test Subnet",
    miner_count: 100,
    validator_count: 50,
    registration_cost: 1.5,
    emission_share: 0.05,
    alpha_price: 0.12,
    alpha_market_cap: 1200,
    fill_rate: 0.78,
    owner_take_rate: 0.18,
    tao_reserves: 500,
    alpha_reserves: 4000,
    subnet_age_days: 120,
    sparkline_emission_7d: [0.04, 0.05],
    sparkline_price_7d: [0.10, 0.12],
    alpha_price_change_24h: 5.0,
    alpha_price_change_7d: 15.0,
    alpha_price_change_30d: 30.0,
    net_tao_inflow: 100.0,
    immunity_active: false,
    ...overrides,
  };
}

describe("prepareBubbleData", () => {
  it("returns empty data for undefined subnets", () => {
    const result = prepareBubbleData(undefined);
    expect(result.data).toEqual([]);
    expect(result.excludedCount).toBe(0);
  });

  it("returns empty data for empty array", () => {
    const result = prepareBubbleData([]);
    expect(result.data).toEqual([]);
    expect(result.excludedCount).toBe(0);
  });

  it("filters out subnets with null alpha_price_change_7d", () => {
    const subnets = [
      makeSubnet({ netuid: 1, alpha_price_change_7d: null }),
      makeSubnet({ netuid: 2, alpha_price_change_7d: 10.0 }),
    ];
    const result = prepareBubbleData(subnets);
    expect(result.data).toHaveLength(1);
    expect(result.data[0].netuid).toBe(2);
    expect(result.excludedCount).toBe(1);
  });

  it("filters out subnets with null net_tao_inflow", () => {
    const subnets = [
      makeSubnet({ netuid: 1, net_tao_inflow: null }),
      makeSubnet({ netuid: 2, net_tao_inflow: 50.0 }),
    ];
    const result = prepareBubbleData(subnets);
    expect(result.data).toHaveLength(1);
    expect(result.data[0].netuid).toBe(2);
    expect(result.excludedCount).toBe(1);
  });

  it("maps valid subnets correctly", () => {
    const subnets = [
      makeSubnet({
        netuid: 3,
        name: "Alpha Net",
        emission_share: 0.05,
        alpha_price_change_7d: 12.5,
        miner_count: 80,
        net_tao_inflow: 200.0,
      }),
    ];
    const result = prepareBubbleData(subnets);
    expect(result.data).toHaveLength(1);
    expect(result.data[0]).toEqual({
      netuid: 3,
      name: "Alpha Net",
      x: 5.0, // emission_share * 100
      y: 12.5,
      z: 80,
      inflow: 200.0,
    });
    expect(result.excludedCount).toBe(0);
  });

  it("uses SN{netuid} fallback when name is null", () => {
    const subnets = [makeSubnet({ netuid: 42, name: null })];
    const result = prepareBubbleData(subnets);
    expect(result.data[0].name).toBe("SN42");
  });

  it("counts multiple excluded subnets correctly", () => {
    const subnets = [
      makeSubnet({ netuid: 1, alpha_price_change_7d: null }),
      makeSubnet({ netuid: 2, net_tao_inflow: null }),
      makeSubnet({
        netuid: 3,
        alpha_price_change_7d: null,
        net_tao_inflow: null,
      }),
      makeSubnet({ netuid: 4 }), // valid
    ];
    const result = prepareBubbleData(subnets);
    expect(result.data).toHaveLength(1);
    expect(result.excludedCount).toBe(3);
  });
});

describe("SubnetBubbleChart", () => {
  beforeEach(() => {
    mockPush.mockClear();
  });

  it("shows skeleton when isLoading is true", () => {
    render(<SubnetBubbleChart subnets={undefined} isLoading={true} />);
    expect(screen.getByLabelText("Loading bubble chart")).toBeInTheDocument();
  });

  it("shows empty state when no valid subnets", () => {
    const subnets = [
      makeSubnet({ netuid: 1, alpha_price_change_7d: null }),
    ];
    render(<SubnetBubbleChart subnets={subnets} isLoading={false} />);
    expect(
      screen.getByText(/No subnets with sufficient data/),
    ).toBeInTheDocument();
  });

  it("shows empty state when subnets is undefined and not loading", () => {
    render(<SubnetBubbleChart subnets={undefined} isLoading={false} />);
    expect(
      screen.getByText(/No subnets with sufficient data/),
    ).toBeInTheDocument();
  });

  it("renders scatter chart with valid subnet data", () => {
    const subnets = [makeSubnet({ netuid: 1 }), makeSubnet({ netuid: 2 })];
    render(<SubnetBubbleChart subnets={subnets} isLoading={false} />);
    expect(screen.getByTestId("scatter-chart")).toBeInTheDocument();
    expect(screen.getByTestId("scatter")).toBeInTheDocument();
  });

  it("renders chart with correct aria-label", () => {
    const subnets = [makeSubnet()];
    render(<SubnetBubbleChart subnets={subnets} isLoading={false} />);
    expect(
      screen.getByLabelText(
        /Bubble chart showing subnet emission share vs 7-day price change/,
      ),
    ).toBeInTheDocument();
  });

  it("renders legend with inflow/outflow indicators", () => {
    const subnets = [makeSubnet()];
    render(<SubnetBubbleChart subnets={subnets} isLoading={false} />);
    expect(screen.getByText("Net TAO Inflow (+)")).toBeInTheDocument();
    expect(screen.getByText(/Net TAO Outflow/)).toBeInTheDocument();
    expect(screen.getByText("Bubble size = miner count")).toBeInTheDocument();
  });

  it("shows excluded subnets count when some are filtered out", () => {
    const subnets = [
      makeSubnet({ netuid: 1 }),
      makeSubnet({ netuid: 2, alpha_price_change_7d: null }),
      makeSubnet({ netuid: 3, net_tao_inflow: null }),
    ];
    render(<SubnetBubbleChart subnets={subnets} isLoading={false} />);
    expect(
      screen.getByText(/2 subnets not shown/),
    ).toBeInTheDocument();
  });

  it("does not show excluded count when all subnets are valid", () => {
    const subnets = [makeSubnet({ netuid: 1 }), makeSubnet({ netuid: 2 })];
    render(<SubnetBubbleChart subnets={subnets} isLoading={false} />);
    expect(screen.queryByText(/not shown/)).not.toBeInTheDocument();
  });

  it("shows singular 'subnet' for single excluded", () => {
    const subnets = [
      makeSubnet({ netuid: 1 }),
      makeSubnet({ netuid: 2, alpha_price_change_7d: null }),
    ];
    render(<SubnetBubbleChart subnets={subnets} isLoading={false} />);
    expect(
      screen.getByText(/1 subnet not shown/),
    ).toBeInTheDocument();
  });

  it("shows error state when isError is true", () => {
    render(
      <SubnetBubbleChart
        subnets={undefined}
        isLoading={false}
        isError={true}
        error={new Error("Network failure")}
        onRetry={vi.fn()}
      />,
    );
    expect(screen.getByText("Failed to load screener data.")).toBeInTheDocument();
    expect(screen.getByText("Network failure")).toBeInTheDocument();
    expect(screen.getByText("Retry")).toBeInTheDocument();
  });

  it("shows error state without retry when onRetry not provided", () => {
    render(
      <SubnetBubbleChart
        subnets={undefined}
        isLoading={false}
        isError={true}
      />,
    );
    expect(screen.getByText("Failed to load screener data.")).toBeInTheDocument();
    expect(screen.queryByText("Retry")).not.toBeInTheDocument();
  });
});

describe("SubnetBubbleChartSkeleton", () => {
  it("renders skeleton with loading label", () => {
    render(<SubnetBubbleChartSkeleton />);
    expect(
      screen.getByLabelText("Loading bubble chart"),
    ).toBeInTheDocument();
  });
});
