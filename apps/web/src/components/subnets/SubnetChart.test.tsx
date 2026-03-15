import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { SubnetChart } from "./SubnetChart";
import type { SubnetHistoryPoint } from "@/types";

// Mock recharts to avoid rendering issues in jsdom
vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  AreaChart: ({ children, data }: { children: React.ReactNode; data: unknown[] }) => (
    <div data-testid="area-chart" data-count={data.length}>{children}</div>
  ),
  Area: ({ dataKey }: { dataKey: string }) => (
    <div data-testid={`area-${dataKey}`} />
  ),
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  CartesianGrid: () => <div data-testid="cartesian-grid" />,
  Tooltip: () => <div data-testid="tooltip" />,
}));

const mockData: SubnetHistoryPoint[] = [
  { time: "2026-03-10T00:00:00Z", emission_share: 0.048, alpha_price: 0.11, miner_count: 98 },
  { time: "2026-03-11T00:00:00Z", emission_share: 0.05, alpha_price: 0.12, miner_count: 100 },
];

describe("SubnetChart", () => {
  it("renders chart label", () => {
    render(
      <SubnetChart data={mockData} dataKey="emission_share" label="Emission Share" />,
    );
    expect(screen.getByText("Emission Share")).toBeInTheDocument();
  });

  it("renders recharts components", () => {
    render(
      <SubnetChart data={mockData} dataKey="alpha_price" label="Alpha Price" />,
    );
    expect(screen.getByTestId("responsive-container")).toBeInTheDocument();
    expect(screen.getByTestId("area-chart")).toBeInTheDocument();
    expect(screen.getByTestId("area-alpha_price")).toBeInTheDocument();
  });

  it("passes correct data count to chart", () => {
    render(
      <SubnetChart data={mockData} dataKey="miner_count" label="Miner Count" />,
    );
    expect(screen.getByTestId("area-chart")).toHaveAttribute("data-count", "2");
  });

  it("renders grid, axes, and tooltip", () => {
    render(
      <SubnetChart data={mockData} dataKey="emission_share" label="Emission" />,
    );
    expect(screen.getByTestId("cartesian-grid")).toBeInTheDocument();
    expect(screen.getByTestId("x-axis")).toBeInTheDocument();
    expect(screen.getByTestId("y-axis")).toBeInTheDocument();
    expect(screen.getByTestId("tooltip")).toBeInTheDocument();
  });
});
