import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
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

// Mock next-auth/react
vi.mock("next-auth/react", () => ({
  useSession: () => ({
    data: { user: { premiumStatus: "premium" } },
    status: "authenticated",
  }),
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
});
