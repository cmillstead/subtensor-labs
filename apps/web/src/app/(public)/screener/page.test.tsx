import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, it, expect, vi } from "vitest";
import ScreenerPage from "./page";

const MOCK_SUBNETS = [
  {
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
  },
  {
    netuid: 2,
    name: "Machine Translation",
    miner_count: 200,
    validator_count: 30,
    registration_cost: 3.0,
    emission_share: 0.10,
    alpha_price: 0.25,
    alpha_market_cap: 2500,
    fill_rate: 0.65,
    owner_take_rate: 0.15,
    tao_reserves: 800,
    alpha_reserves: 3200,
    subnet_age_days: 60,
    sparkline_emission_7d: [0.08, 0.10],
    sparkline_price_7d: [0.22, 0.25],
    alpha_price_change_24h: -2.0,
    alpha_price_change_7d: 8.0,
    alpha_price_change_30d: -10.0,
    net_tao_inflow: -50.0,
    immunity_active: false,
  },
];

// Mock useScreener hook
vi.mock("@/hooks/useScreener", () => ({
  useScreener: vi.fn(() => ({
    data: {
      data: {
        subnets: MOCK_SUBNETS,
        subnet_count: 2,
      },
      meta: {
        last_updated: "2026-03-14T00:00:00Z",
        cache_hit: false,
        compute_ms: 42,
      },
    },
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
  })),
}));

// Default: premium user
let mockSession: unknown = {
  data: { user: { premiumStatus: "premium" } },
  status: "authenticated",
};

vi.mock("next-auth/react", () => ({
  useSession: () => mockSession,
}));

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

// Mock recharts
vi.mock("recharts", () => ({
  LineChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="line-chart">{children}</div>
  ),
  Line: (props: { stroke: string }) => (
    <div data-testid="line" data-stroke={props.stroke} />
  ),
  ScatterChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="scatter-chart">{children}</div>
  ),
  Scatter: (props: { data?: unknown[] }) => (
    <div data-testid="scatter" data-count={props.data?.length ?? 0} />
  ),
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  ZAxis: () => <div data-testid="z-axis" />,
  CartesianGrid: () => <div data-testid="cartesian-grid" />,
  Tooltip: () => <div data-testid="tooltip" />,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
}));

// Mock ResizeObserver
class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = ResizeObserverMock;

describe("ScreenerPage", () => {
  beforeEach(() => {
    mockSession = {
      data: { user: { premiumStatus: "premium" } },
      status: "authenticated",
    };
  });

  it("renders page title and description", () => {
    render(<ScreenerPage />);
    expect(
      screen.getByText("Subnet Screener"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Browse and compare all active Bittensor subnets."),
    ).toBeInTheDocument();
  });

  it("renders ScreenerTable with subnet data", () => {
    render(<ScreenerPage />);
    expect(screen.getByText("SN1")).toBeInTheDocument();
    expect(screen.getByText("· Text Prompting")).toBeInTheDocument();
  });

  it("shows subnet count when no filters active", () => {
    render(<ScreenerPage />);
    expect(screen.getByText("Showing 2 subnets")).toBeInTheDocument();
  });

  it("shows LastUpdated from meta", () => {
    render(<ScreenerPage />);
    expect(screen.getByText(/ago|just now|Updated/i)).toBeInTheDocument();
  });

  it("renders FilterPanel with basic and advanced sections", () => {
    render(<ScreenerPage />);
    expect(screen.getByText("Basic Filters")).toBeInTheDocument();
    expect(screen.getByText("Advanced Filters")).toBeInTheDocument();
  });

  it("renders advanced filter controls for premium user", () => {
    render(<ScreenerPage />);
    expect(screen.getByText("Price Change 24h")).toBeInTheDocument();
    expect(screen.getByText("Net TAO Inflow")).toBeInTheDocument();
    expect(screen.getByLabelText("Immunity Status")).toBeInTheDocument();
  });

  it("renders Filters heading from FilterPanel", () => {
    render(<ScreenerPage />);
    expect(screen.getAllByText("Filters").length).toBeGreaterThanOrEqual(1);
  });

  // View toggle tests
  it("renders ViewToggle component", () => {
    render(<ScreenerPage />);
    expect(screen.getByText("Table")).toBeInTheDocument();
    expect(screen.getByText("Chart")).toBeInTheDocument();
  });

  it("defaults to table view", () => {
    render(<ScreenerPage />);
    const tableBtn = screen.getByText("Table").closest("button")!;
    expect(tableBtn).toHaveAttribute("aria-pressed", "true");
    // Table should be rendered (subnet data visible)
    expect(screen.getByText("SN1")).toBeInTheDocument();
  });

  it("switches to chart view when Chart button clicked", async () => {
    const user = userEvent.setup();
    render(<ScreenerPage />);
    await user.click(screen.getByText("Chart"));

    // Chart should be rendered
    expect(screen.getByTestId("scatter-chart")).toBeInTheDocument();
    // Table data should not be visible
    expect(screen.queryByText("SN1")).not.toBeInTheDocument();
  });

  it("switches back to table view from chart", async () => {
    const user = userEvent.setup();
    render(<ScreenerPage />);

    // Switch to chart
    await user.click(screen.getByText("Chart"));
    expect(screen.getByTestId("scatter-chart")).toBeInTheDocument();

    // Switch back to table
    await user.click(screen.getByText("Table"));
    expect(screen.getByText("SN1")).toBeInTheDocument();
    expect(screen.queryByTestId("scatter-chart")).not.toBeInTheDocument();
  });

  it("shows bubble chart without PremiumGate for premium users", async () => {
    const user = userEvent.setup();
    render(<ScreenerPage />);
    await user.click(screen.getByText("Chart"));

    expect(screen.getByTestId("scatter-chart")).toBeInTheDocument();
    // PremiumGate shows "Upgrade to Premium" — should NOT be present
    expect(screen.queryByText("Upgrade to Premium")).not.toBeInTheDocument();
  });

  it("wraps bubble chart in PremiumGate for free users", async () => {
    mockSession = {
      data: { user: { premiumStatus: "free" } },
      status: "authenticated",
    };
    const user = userEvent.setup();
    render(<ScreenerPage />);
    await user.click(screen.getByText("Chart"));

    // PremiumGate should render
    expect(screen.getAllByText("Upgrade to Premium").length).toBeGreaterThanOrEqual(1);
  });

  it("wraps bubble chart in PremiumGate for unauthenticated users", async () => {
    mockSession = {
      data: null,
      status: "unauthenticated",
    };
    const user = userEvent.setup();
    render(<ScreenerPage />);
    await user.click(screen.getByText("Chart"));

    expect(screen.getAllByText("Upgrade to Premium").length).toBeGreaterThanOrEqual(1);
  });

  it("preserves subnet count across view switches", async () => {
    const user = userEvent.setup();
    render(<ScreenerPage />);

    expect(screen.getByText("Showing 2 subnets")).toBeInTheDocument();

    await user.click(screen.getByText("Chart"));
    expect(screen.getByText("Showing 2 subnets")).toBeInTheDocument();

    await user.click(screen.getByText("Table"));
    expect(screen.getByText("Showing 2 subnets")).toBeInTheDocument();
  });
});
