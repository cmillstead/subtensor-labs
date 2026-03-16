import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { FilterPanel } from "./FilterPanel";
import type { ScreenerSubnet } from "@/types";
import { EMPTY_FILTERS } from "@/hooks/useScreenerFilters";

const mockUseSession = vi.fn();

vi.mock("next-auth/react", () => ({
  useSession: () => mockUseSession(),
}));

const MOCK_SUBNETS: ScreenerSubnet[] = [
  {
    netuid: 1,
    name: "Test",
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
];

const defaultProps = {
  filters: EMPTY_FILTERS,
  onFilterChange: vi.fn(),
  onReset: vi.fn(),
  activeFilterCount: 0,
  subnetData: MOCK_SUBNETS,
};

describe("FilterPanel", () => {
  beforeEach(() => {
    // Default: premium user (full access)
    mockUseSession.mockReturnValue({
      data: { user: { premiumStatus: "premium" } },
      status: "authenticated",
    });
  });

  it("renders all 6 basic filter controls", () => {
    render(<FilterPanel {...defaultProps} />);
    expect(screen.getByText("Miner Count")).toBeInTheDocument();
    expect(screen.getByText("Validator Count")).toBeInTheDocument();
    expect(screen.getByText("Registration Cost")).toBeInTheDocument();
    expect(screen.getByText("Emission Share")).toBeInTheDocument();
    expect(screen.getByText("Alpha Price")).toBeInTheDocument();
    expect(screen.getByText("Subnet Age")).toBeInTheDocument();
  });

  it("renders all 7 advanced range filter controls for premium users", () => {
    render(<FilterPanel {...defaultProps} />);
    expect(screen.getByText("Price Change 24h")).toBeInTheDocument();
    expect(screen.getByText("Price Change 7d")).toBeInTheDocument();
    expect(screen.getByText("Price Change 30d")).toBeInTheDocument();
    expect(screen.getByText("Alpha Market Cap")).toBeInTheDocument();
    expect(screen.getByText("Net TAO Inflow")).toBeInTheDocument();
    expect(screen.getByText("Fill Rate")).toBeInTheDocument();
    expect(screen.getByText("Owner Take Rate")).toBeInTheDocument();
  });

  it("renders immunity status toggle for premium users", () => {
    render(<FilterPanel {...defaultProps} />);
    expect(screen.getByLabelText("Immunity Status")).toBeInTheDocument();
    expect(screen.getByText("All")).toBeInTheDocument();
    expect(screen.getByText("Active (Immune)")).toBeInTheDocument();
    expect(screen.getByText("Expired")).toBeInTheDocument();
  });

  it("renders section headers", () => {
    render(<FilterPanel {...defaultProps} />);
    expect(screen.getByText("Basic Filters")).toBeInTheDocument();
    expect(screen.getByText("Advanced Filters")).toBeInTheDocument();
  });

  it("shows PremiumBadge next to Advanced Filters header", () => {
    render(<FilterPanel {...defaultProps} />);
    // The PremiumBadge renders "Premium" text
    expect(screen.getByText("Premium")).toBeInTheDocument();
  });

  it("does not show Reset Filters button when no filters are active", () => {
    render(<FilterPanel {...defaultProps} activeFilterCount={0} />);
    expect(screen.queryByText("Reset Filters")).not.toBeInTheDocument();
  });

  it("shows Reset Filters button when filters are active", () => {
    render(<FilterPanel {...defaultProps} activeFilterCount={2} />);
    expect(screen.getByText("Reset Filters")).toBeInTheDocument();
  });

  it("calls onReset when Reset Filters is clicked", async () => {
    const onReset = vi.fn();
    render(
      <FilterPanel {...defaultProps} activeFilterCount={1} onReset={onReset} />,
    );

    await userEvent.click(screen.getByText("Reset Filters"));
    expect(onReset).toHaveBeenCalledTimes(1);
  });

  it("shows active filter count in desktop header", () => {
    render(<FilterPanel {...defaultProps} activeFilterCount={3} />);
    expect(screen.getByText("3 active")).toBeInTheDocument();
  });

  it("does not show active count when no filters active", () => {
    render(<FilterPanel {...defaultProps} activeFilterCount={0} />);
    expect(screen.queryByText(/active/)).not.toBeInTheDocument();
  });

  it("renders mobile toggle button with Filters text", () => {
    render(<FilterPanel {...defaultProps} />);
    const toggleButton = screen.getByRole("button", { name: /Filters/i });
    expect(toggleButton).toBeInTheDocument();
  });

  it("mobile toggle shows active filter count badge", () => {
    render(<FilterPanel {...defaultProps} activeFilterCount={2} />);
    expect(screen.getByText("2")).toBeInTheDocument();
  });

  it("calls onFilterChange when a filter value is entered", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const onFilterChange = vi.fn();
    render(
      <FilterPanel {...defaultProps} onFilterChange={onFilterChange} />,
    );

    const minInput = screen.getByLabelText("Miner Count minimum");
    await userEvent.type(minInput, "50");

    vi.advanceTimersByTime(300);
    expect(onFilterChange).toHaveBeenCalled();
    vi.useRealTimers();
  });

  it("converts emission share display values to decimals for filter state", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const onFilterChange = vi.fn();
    render(
      <FilterPanel {...defaultProps} onFilterChange={onFilterChange} />,
    );

    const minInput = screen.getByLabelText("Emission Share minimum");
    await userEvent.type(minInput, "5");

    vi.advanceTimersByTime(300);
    expect(onFilterChange).toHaveBeenCalled();
    const lastCall =
      onFilterChange.mock.calls[onFilterChange.mock.calls.length - 1][0];
    expect(lastCall.min_emission_share).toBeCloseTo(0.05);
    vi.useRealTimers();
  });

  describe("premium gating", () => {
    it("basic filters remain functional for free users", () => {
      mockUseSession.mockReturnValue({
        data: { user: { premiumStatus: "free" } },
        status: "authenticated",
      });

      render(<FilterPanel {...defaultProps} />);

      // Basic filters should still be accessible
      expect(screen.getByText("Miner Count")).toBeInTheDocument();
      expect(screen.getByLabelText("Miner Count minimum")).toBeInTheDocument();
    });

    it("advanced filters are gated behind PremiumGate for free users", () => {
      mockUseSession.mockReturnValue({
        data: { user: { premiumStatus: "free" } },
        status: "authenticated",
      });

      render(<FilterPanel {...defaultProps} />);

      // PremiumGate shows upgrade overlay for free users
      expect(screen.getByText("Upgrade to Premium")).toBeInTheDocument();
    });

    it("advanced filters are fully functional for premium users", () => {
      mockUseSession.mockReturnValue({
        data: { user: { premiumStatus: "premium" } },
        status: "authenticated",
      });

      render(<FilterPanel {...defaultProps} />);

      // No upgrade overlay
      expect(
        screen.queryByText("Upgrade to Premium"),
      ).not.toBeInTheDocument();

      // Advanced filters are accessible
      expect(
        screen.getByLabelText("Price Change 24h minimum"),
      ).toBeInTheDocument();
    });

    it("advanced filters are gated for unauthenticated users", () => {
      mockUseSession.mockReturnValue({
        data: null,
        status: "unauthenticated",
      });

      render(<FilterPanel {...defaultProps} />);

      expect(screen.getByText("Upgrade to Premium")).toBeInTheDocument();
    });
  });

  describe("immunity filter", () => {
    it("calls onFilterChange with immunity_active when immunity select changes", async () => {
      const onFilterChange = vi.fn();
      render(
        <FilterPanel {...defaultProps} onFilterChange={onFilterChange} />,
      );

      const select = screen.getByLabelText("Immunity Status");
      await userEvent.selectOptions(select, "active");

      expect(onFilterChange).toHaveBeenCalledWith(
        expect.objectContaining({ immunity_active: true }),
      );
    });

    it("sets immunity_active to null when 'All' is selected", async () => {
      const onFilterChange = vi.fn();
      render(
        <FilterPanel
          {...defaultProps}
          filters={{ ...EMPTY_FILTERS, immunity_active: true }}
          onFilterChange={onFilterChange}
        />,
      );

      const select = screen.getByLabelText("Immunity Status");
      await userEvent.selectOptions(select, "all");

      expect(onFilterChange).toHaveBeenCalledWith(
        expect.objectContaining({ immunity_active: null }),
      );
    });
  });
});
