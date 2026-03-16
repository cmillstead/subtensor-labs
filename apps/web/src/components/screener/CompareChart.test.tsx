import React from "react";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, it, expect, vi } from "vitest";
import { CompareChart, prepareCompareChartData } from "./CompareChart";
import type { SubnetHistoryPoint } from "@/types";

// Mock recharts
vi.mock("recharts", () => ({
  LineChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="line-chart">{children}</div>
  ),
  Line: (props: { stroke: string; dataKey: string }) => (
    <div data-testid="line" data-stroke={props.stroke} data-key={props.dataKey} />
  ),
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  CartesianGrid: () => <div data-testid="cartesian-grid" />,
  Tooltip: () => <div data-testid="tooltip" />,
  Legend: () => <div data-testid="legend" />,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
}));

const mockUseSubnet = vi.fn();
vi.mock("@/hooks/useSubnet", () => ({
  useSubnet: (...args: unknown[]) => mockUseSubnet(...args),
}));

// Mock ResizeObserver
class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = ResizeObserverMock;

const HISTORY_1: SubnetHistoryPoint[] = [
  { time: "2026-03-01T00:00:00Z", emission_share: 0.05, alpha_price: 0.12, miner_count: 100 },
  { time: "2026-03-02T00:00:00Z", emission_share: 0.06, alpha_price: 0.13, miner_count: 101 },
];

const HISTORY_2: SubnetHistoryPoint[] = [
  { time: "2026-03-01T00:00:00Z", emission_share: 0.08, alpha_price: 0.25, miner_count: 200 },
  { time: "2026-03-02T00:00:00Z", emission_share: 0.09, alpha_price: 0.26, miner_count: 201 },
];

describe("prepareCompareChartData", () => {
  it("merges histories by time and maps metric values", () => {
    const result = prepareCompareChartData(
      [HISTORY_1, HISTORY_2],
      [1, 3],
      ["SN1", "SN3"],
      "emission_share",
    );
    expect(result.length).toBe(2);
    expect(result[0]).toHaveProperty("SN1", 0.05);
    expect(result[0]).toHaveProperty("SN3", 0.08);
    expect(result[1]).toHaveProperty("SN1", 0.06);
    expect(result[1]).toHaveProperty("SN3", 0.09);
  });

  it("handles alpha_price metric", () => {
    const result = prepareCompareChartData(
      [HISTORY_1, HISTORY_2],
      [1, 3],
      ["SN1", "SN3"],
      "alpha_price",
    );
    expect(result[0]).toHaveProperty("SN1", 0.12);
    expect(result[0]).toHaveProperty("SN3", 0.25);
  });

  it("returns empty array when no histories", () => {
    const result = prepareCompareChartData(
      [undefined, undefined],
      [1, 3],
      ["SN1", "SN3"],
      "emission_share",
    );
    expect(result).toEqual([]);
  });

  it("handles mismatched time points with null fill", () => {
    const h1: SubnetHistoryPoint[] = [
      { time: "2026-03-01T00:00:00Z", emission_share: 0.05, alpha_price: 0.12, miner_count: 100 },
    ];
    const h2: SubnetHistoryPoint[] = [
      { time: "2026-03-02T00:00:00Z", emission_share: 0.08, alpha_price: 0.25, miner_count: 200 },
    ];
    const result = prepareCompareChartData([h1, h2], [1, 3], ["SN1", "SN3"], "emission_share");
    expect(result.length).toBe(2);
    expect(result[0]).toHaveProperty("SN1", 0.05);
    expect(result[0]).toHaveProperty("SN3", null);
    expect(result[1]).toHaveProperty("SN1", null);
    expect(result[1]).toHaveProperty("SN3", 0.08);
  });

  it("formats time as short date", () => {
    const result = prepareCompareChartData(
      [HISTORY_1],
      [1],
      ["SN1"],
      "emission_share",
    );
    // Time should be formatted as "Mon Day" style (locale-dependent)
    expect(typeof result[0].time).toBe("string");
    expect(result[0].time.length).toBeGreaterThan(0);
  });
});

describe("CompareChart", () => {
  beforeEach(() => {
    mockUseSubnet.mockReturnValue({
      data: {
        data: {
          history: HISTORY_1,
        },
      },
      isLoading: false,
      isError: false,
    });
  });

  it("renders chart with title", () => {
    render(
      <CompareChart
        netuids={[1, 3]}
        subnetNames={["SN1", "SN3"]}
        metric="emission_share"
        label="Emission Share"
      />
    );
    expect(screen.getByText("Emission Share")).toBeInTheDocument();
    expect(screen.getByTestId("line-chart")).toBeInTheDocument();
  });

  it("renders line per subnet", () => {
    render(
      <CompareChart
        netuids={[1, 3]}
        subnetNames={["SN1", "SN3"]}
        metric="emission_share"
        label="Emission Share"
      />
    );
    const lines = screen.getAllByTestId("line");
    expect(lines.length).toBe(2);
    expect(lines[0]).toHaveAttribute("data-stroke", "#8B5CF6"); // violet
    expect(lines[1]).toHaveAttribute("data-stroke", "#3B82F6"); // blue
  });

  it("uses distinct colors for 3 subnets", () => {
    render(
      <CompareChart
        netuids={[1, 3, 19]}
        subnetNames={["SN1", "SN3", "SN19"]}
        metric="emission_share"
        label="Emission Share"
      />
    );
    const lines = screen.getAllByTestId("line");
    expect(lines.length).toBe(3);
    expect(lines[0]).toHaveAttribute("data-stroke", "#8B5CF6"); // violet
    expect(lines[1]).toHaveAttribute("data-stroke", "#3B82F6"); // blue
    expect(lines[2]).toHaveAttribute("data-stroke", "#10B981"); // emerald
  });

  it("shows loading state", () => {
    mockUseSubnet.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    });
    render(
      <CompareChart
        netuids={[1, 3]}
        subnetNames={["SN1", "SN3"]}
        metric="emission_share"
        label="Emission Share"
      />
    );
    expect(screen.getByLabelText("Loading Emission Share chart")).toBeInTheDocument();
  });

  it("shows error state", () => {
    mockUseSubnet.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    });
    render(
      <CompareChart
        netuids={[1, 3]}
        subnetNames={["SN1", "SN3"]}
        metric="emission_share"
        label="Emission Share"
      />
    );
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText("Failed to load chart data.")).toBeInTheDocument();
  });

  it("has aria-label on chart container", () => {
    render(
      <CompareChart
        netuids={[1, 3]}
        subnetNames={["SN1", "SN3"]}
        metric="emission_share"
        label="Emission Share"
      />
    );
    expect(screen.getByRole("img", { name: "Emission Share comparison chart" })).toBeInTheDocument();
  });
});
