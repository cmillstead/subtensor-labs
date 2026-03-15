import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { FilterPanel } from "./FilterPanel";
import type { ScreenerFilter, ScreenerSubnet } from "@/types";

const EMPTY_FILTERS: ScreenerFilter = {
  min_miners: null,
  max_miners: null,
  min_validators: null,
  max_validators: null,
  min_registration_cost: null,
  max_registration_cost: null,
  min_emission_share: null,
  max_emission_share: null,
  min_alpha_price: null,
  max_alpha_price: null,
  min_subnet_age_days: null,
  max_subnet_age_days: null,
  sort_by: "emission_share",
  sort_direction: "desc",
};

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
  it("renders all six filter controls with labels", () => {
    render(<FilterPanel {...defaultProps} />);
    expect(screen.getByText("Miner Count")).toBeInTheDocument();
    expect(screen.getByText("Validator Count")).toBeInTheDocument();
    expect(screen.getByText("Registration Cost")).toBeInTheDocument();
    expect(screen.getByText("Emission Share")).toBeInTheDocument();
    expect(screen.getByText("Alpha Price")).toBeInTheDocument();
    expect(screen.getByText("Subnet Age")).toBeInTheDocument();
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
    // Mobile toggle button exists in DOM (hidden via CSS on desktop)
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

    // User types "5" meaning 5% — should store as 0.05
    const minInput = screen.getByLabelText("Emission Share minimum");
    await userEvent.type(minInput, "5");

    vi.advanceTimersByTime(300);
    expect(onFilterChange).toHaveBeenCalled();
    const lastCall =
      onFilterChange.mock.calls[onFilterChange.mock.calls.length - 1][0];
    expect(lastCall.min_emission_share).toBeCloseTo(0.05);
    vi.useRealTimers();
  });
});
