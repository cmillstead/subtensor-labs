import React from "react";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { SubnetCompare, determineBestValues, METRICS } from "./SubnetCompare";
import type { ScreenerSubnet } from "@/types";

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

// Mock useSubnet
vi.mock("@/hooks/useSubnet", () => ({
  useSubnet: vi.fn(() => ({
    data: {
      data: {
        history: [
          { time: "2026-03-01", emission_share: 0.05, alpha_price: 0.12, miner_count: 100 },
          { time: "2026-03-02", emission_share: 0.06, alpha_price: 0.13, miner_count: 101 },
        ],
      },
    },
    isLoading: false,
    isError: false,
  })),
}));

// Mock ResizeObserver
class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = ResizeObserverMock;

function mockSubnet(overrides: Partial<ScreenerSubnet> = {}): ScreenerSubnet {
  return {
    netuid: 1,
    name: "Text Prompting",
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

const subnet1 = mockSubnet({ netuid: 1, name: "Text Prompting", miner_count: 100, registration_cost: 1.5, emission_share: 0.05 });
const subnet2 = mockSubnet({ netuid: 3, name: "Data Scraping", miner_count: 200, registration_cost: 3.0, emission_share: 0.08 });
const subnet3 = mockSubnet({ netuid: 19, name: "Vision", miner_count: 150, registration_cost: 0.5, emission_share: 0.03 });

describe("SubnetCompare", () => {
  it("renders comparison table with 2 subnets", () => {
    render(<SubnetCompare subnets={[subnet1, subnet2]} onClose={vi.fn()} />);
    expect(screen.getByText("Subnet Comparison")).toBeInTheDocument();
    expect(screen.getByText(/SN1/)).toBeInTheDocument();
    expect(screen.getByText(/SN3/)).toBeInTheDocument();
  });

  it("renders comparison table with 3 subnets", () => {
    render(<SubnetCompare subnets={[subnet1, subnet2, subnet3]} onClose={vi.fn()} />);
    const headers = screen.getAllByRole("columnheader");
    // Metric + 3 subnet columns = 4
    expect(headers.length).toBe(4);
  });

  it("renders all metric rows", () => {
    render(<SubnetCompare subnets={[subnet1, subnet2]} onClose={vi.fn()} />);
    // Check metric labels in the table body
    const table = screen.getByRole("table");
    expect(within(table).getByText("Miners")).toBeInTheDocument();
    expect(within(table).getByText("Validators")).toBeInTheDocument();
    expect(within(table).getByText("Reg Cost")).toBeInTheDocument();
    expect(within(table).getByText("Emission %")).toBeInTheDocument();
    expect(within(table).getByText("Alpha Price")).toBeInTheDocument();
    expect(within(table).getByText("Market Cap")).toBeInTheDocument();
    expect(within(table).getByText("Fill Rate")).toBeInTheDocument();
    expect(within(table).getByText("Owner Take")).toBeInTheDocument();
    expect(within(table).getByText("TAO Reserves")).toBeInTheDocument();
    expect(within(table).getByText("7d Price Change")).toBeInTheDocument();
    expect(within(table).getByText("Net TAO Inflow")).toBeInTheDocument();
  });

  it("highlights best values with emerald color", () => {
    render(<SubnetCompare subnets={[subnet1, subnet2]} onClose={vi.fn()} />);
    // SN3 has higher miner_count (200 > 100), should be emerald
    const rows = screen.getAllByRole("row");
    // Find the Miners row (first body row after header)
    const minersRow = rows.find((r) => within(r).queryByText("Miners"));
    expect(minersRow).toBeDefined();
    // The SN3 cell in miners row should have emerald text
    const cells = within(minersRow!).getAllByRole("cell");
    // cells[0] = "Miners" label, cells[1] = SN1 value, cells[2] = SN3 value
    expect(cells[2]).toHaveClass("text-emerald-400");
    expect(cells[1]).not.toHaveClass("text-emerald-400");
  });

  it("calls onClose when Back button clicked", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(<SubnetCompare subnets={[subnet1, subnet2]} onClose={onClose} />);
    await user.click(screen.getByRole("button", { name: "Back to Screener" }));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("shows empty state when no subnets", () => {
    render(<SubnetCompare subnets={[]} onClose={vi.fn()} />);
    expect(screen.getByText("No subnets selected for comparison.")).toBeInTheDocument();
  });

  it("renders historical charts", () => {
    render(<SubnetCompare subnets={[subnet1, subnet2]} onClose={vi.fn()} />);
    // Should have 2 chart sections with aria labels
    expect(screen.getByRole("img", { name: "Emission Share comparison chart" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Alpha Price comparison chart" })).toBeInTheDocument();
  });

  it("shows subnet names with colors in header", () => {
    render(<SubnetCompare subnets={[subnet1, subnet2]} onClose={vi.fn()} />);
    const headers = screen.getAllByRole("columnheader");
    // First header is "Metric", then subnet headers
    expect(headers[1]).toHaveStyle({ color: "rgb(139, 92, 246)" }); // violet
    expect(headers[2]).toHaveStyle({ color: "rgb(59, 130, 246)" }); // blue
  });
});

describe("determineBestValues", () => {
  it("returns index of best value per metric (higher is better)", () => {
    const subnets = [subnet1, subnet2]; // SN1: 100 miners, SN3: 200 miners
    const result = determineBestValues(subnets, METRICS);
    expect(result.get("miner_count")).toBe(1); // index 1 = SN3 (200 miners)
  });

  it("returns index of best value per metric (lower is better)", () => {
    const subnets = [subnet1, subnet2]; // SN1: 1.5 reg cost, SN3: 3.0 reg cost
    const result = determineBestValues(subnets, METRICS);
    expect(result.get("registration_cost")).toBe(0); // index 0 = SN1 (1.5 lower)
  });

  it("handles null values gracefully", () => {
    const s1 = mockSubnet({ netuid: 1, alpha_price_change_7d: null });
    const s2 = mockSubnet({ netuid: 2, alpha_price_change_7d: 10 });
    const result = determineBestValues([s1, s2], METRICS);
    expect(result.get("alpha_price_change_7d")).toBe(1); // only s2 has a value
  });

  it("handles 3 subnets correctly", () => {
    const result = determineBestValues([subnet1, subnet2, subnet3], METRICS);
    // Miners: SN3=200 is best (index 1)
    expect(result.get("miner_count")).toBe(1);
    // Reg cost: SN19=0.5 is best (index 2, lower is better)
    expect(result.get("registration_cost")).toBe(2);
    // Emission: SN3=0.08 is best (index 1)
    expect(result.get("emission_share")).toBe(1);
  });
});
