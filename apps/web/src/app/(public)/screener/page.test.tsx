import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import ScreenerPage from "./page";

// Mock useScreener hook
vi.mock("@/hooks/useScreener", () => ({
  useScreener: vi.fn(() => ({
    data: {
      data: {
        subnets: [
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
          },
        ],
        subnet_count: 1,
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

// Mock recharts
vi.mock("recharts", () => ({
  LineChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="line-chart">{children}</div>
  ),
  Line: (props: { stroke: string }) => (
    <div data-testid="line" data-stroke={props.stroke} />
  ),
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
}));

describe("ScreenerPage", () => {
  it("renders page title and description", () => {
    render(<ScreenerPage />);
    expect(
      screen.getByText("Subnet Screener")
    ).toBeInTheDocument();
    expect(
      screen.getByText("Browse and compare all active Bittensor subnets.")
    ).toBeInTheDocument();
  });

  it("renders ScreenerTable with subnet data", () => {
    render(<ScreenerPage />);
    expect(screen.getByText("SN1")).toBeInTheDocument();
    expect(screen.getByText("· Text Prompting")).toBeInTheDocument();
  });

  it("shows subnet count", () => {
    render(<ScreenerPage />);
    expect(screen.getByText("Showing 1 subnet")).toBeInTheDocument();
  });

  it("shows LastUpdated from meta", () => {
    render(<ScreenerPage />);
    // LastUpdated renders a relative time string
    expect(screen.getByText(/ago|just now|Updated/i)).toBeInTheDocument();
  });
});
