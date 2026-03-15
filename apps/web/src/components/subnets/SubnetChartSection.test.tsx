import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { SubnetChartSection } from "./SubnetChartSection";
import type { SubnetDetailResult } from "@/types";

// Mock recharts to avoid rendering issues in jsdom
vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  AreaChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="area-chart">{children}</div>
  ),
  Area: ({ dataKey }: { dataKey: string }) => (
    <div data-testid={`area-${dataKey}`} />
  ),
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  CartesianGrid: () => <div data-testid="cartesian-grid" />,
  Tooltip: () => <div data-testid="tooltip" />,
}));

const mockData: SubnetDetailResult = {
  detail: {
    netuid: 1,
    name: "Test",
    miner_count: 10,
    validator_count: 5,
    registration_cost: 1.0,
    emission_share: 0.05,
    alpha_price: 0.1,
    alpha_market_cap: 100,
    tao_reserves: 50,
    alpha_reserves: 500,
    fill_rate: 0.8,
    owner_take_rate: 0.1,
    subnet_age_days: 30,
    description: null,
  },
  history: [
    { time: "2026-03-10T00:00:00Z", emission_share: 0.04, alpha_price: 0.09, miner_count: 9 },
    { time: "2026-03-11T00:00:00Z", emission_share: 0.05, alpha_price: 0.10, miner_count: 10 },
  ],
  miners: [],
  validators: [],
};

describe("SubnetChartSection", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ data: mockData, meta: { last_updated: "2026-03-15T00:00:00Z", cache_hit: false, compute_ms: 10 } }), { status: 200 }),
    );
  });

  it("renders section title", () => {
    render(<SubnetChartSection initialData={mockData} netuid={1} />);
    expect(screen.getByText("Historical Charts")).toBeInTheDocument();
  });

  it("renders three chart labels", () => {
    render(<SubnetChartSection initialData={mockData} netuid={1} />);
    expect(screen.getByText("Emission Share")).toBeInTheDocument();
    expect(screen.getByText("Alpha Price (τ)")).toBeInTheDocument();
    expect(screen.getByText("Miner Count")).toBeInTheDocument();
  });

  it("renders time range selector with 30D default", () => {
    render(<SubnetChartSection initialData={mockData} netuid={1} />);
    const selected = screen.getByRole("radio", { checked: true });
    expect(selected).toHaveTextContent("30D");
  });

  it("allows switching time range", async () => {
    const user = userEvent.setup();
    render(<SubnetChartSection initialData={mockData} netuid={1} />);

    const sevenDayButton = screen.getByRole("radio", { name: /7D/i });
    await user.click(sevenDayButton);

    expect(sevenDayButton).toHaveAttribute("aria-checked", "true");
  });
});
