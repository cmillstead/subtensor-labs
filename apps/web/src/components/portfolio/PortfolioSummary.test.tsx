import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { PortfolioSummary, PortfolioSkeleton } from "./PortfolioSummary";
import type { PortfolioResult } from "@/types";

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-03-14T15:00:00Z"));
});

afterEach(() => {
  vi.useRealTimers();
});

const mockPortfolio: PortfolioResult = {
  total_value_tao: 12456.78,
  free_balance_tao: 500,
  staked_tao: 10000,
  alpha_value_tao: 1956.78,
  positions: [
    {
      netuid: 1,
      subnet_name: "SN1",
      hotkey: "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty",
      staked_tao: 5000,
      alpha_holdings: 100,
      alpha_value_tao: 978.39,
      emission_share: 0.15,
      incentive: 0,
      trust: 0.9,
      dividends: 0.1,
      is_active: true,
      is_miner: false,
      delegations: [],
    },
    {
      netuid: 3,
      subnet_name: "SN3",
      hotkey: "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY",
      staked_tao: 5000,
      alpha_holdings: 200,
      alpha_value_tao: 978.39,
      emission_share: 0.1,
      incentive: 0,
      trust: 0.8,
      dividends: 0.05,
      is_active: true,
      is_miner: false,
      delegations: [],
    },
  ],
  addresses: ["5DTest1", "5DTest2"],
  last_updated: "2026-03-14T14:58:00Z",
  change_24h_pct: null,
  change_7d_pct: null,
};

describe("PortfolioSummary", () => {
  it("renders total portfolio value", () => {
    render(<PortfolioSummary portfolio={mockPortfolio} />);
    expect(screen.getByText(/12,456\.78/)).toBeInTheDocument();
  });

  it("renders subnet count", () => {
    render(<PortfolioSummary portfolio={mockPortfolio} />);
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(screen.getByText("subnets")).toBeInTheDocument();
  });

  it("renders singular subnet label for 1 position", () => {
    const singleSubnet = {
      ...mockPortfolio,
      positions: [mockPortfolio.positions[0]],
    };
    render(<PortfolioSummary portfolio={singleSubnet} />);
    expect(screen.getByText("subnet")).toBeInTheDocument();
  });

  it("renders 24h change when provided", () => {
    render(<PortfolioSummary portfolio={mockPortfolio} change24h={4.2} />);
    expect(screen.getByText(/\+4\.2%/)).toBeInTheDocument();
  });

  it("renders 7d change when provided", () => {
    render(<PortfolioSummary portfolio={mockPortfolio} change7d={-2.1} />);
    expect(screen.getByText(/-2\.1%/)).toBeInTheDocument();
  });

  it("hides change indicators when null", () => {
    render(<PortfolioSummary portfolio={mockPortfolio} />);
    expect(screen.queryByText(/↑/)).not.toBeInTheDocument();
    expect(screen.queryByText(/↓/)).not.toBeInTheDocument();
  });

  it("renders last updated timestamp", () => {
    render(<PortfolioSummary portfolio={mockPortfolio} />);
    expect(screen.getByText(/2 min ago/)).toBeInTheDocument();
  });

  it("has accessible section label", () => {
    render(<PortfolioSummary portfolio={mockPortfolio} />);
    expect(
      screen.getByLabelText(/Portfolio summary showing total value/),
    ).toBeInTheDocument();
  });

  it("uses gradient background", () => {
    const { container } = render(
      <PortfolioSummary portfolio={mockPortfolio} />,
    );
    const section = container.querySelector("section");
    expect(section?.style.background).toContain("linear-gradient");
  });
});

describe("PortfolioSkeleton", () => {
  it("renders loading state with aria label", () => {
    render(<PortfolioSkeleton />);
    expect(
      screen.getByLabelText(/Loading portfolio summary/),
    ).toBeInTheDocument();
  });

  it("has animate-pulse class", () => {
    const { container } = render(<PortfolioSkeleton />);
    expect(container.firstChild).toHaveClass("animate-pulse");
  });
});
