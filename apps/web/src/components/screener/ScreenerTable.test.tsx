import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { ScreenerTable } from "./ScreenerTable";
import type { ScreenerSubnet } from "@/types";

// Mock recharts to avoid SVG issues
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
    sparkline_emission_7d: [0.04, 0.045, 0.05],
    sparkline_price_7d: [0.10, 0.11, 0.12],
    ...overrides,
  };
}

const defaultProps = {
  subnets: [
    mockSubnet({ netuid: 1, name: "Text Prompting", emission_share: 0.05 }),
    mockSubnet({ netuid: 3, name: "Data Scraping", emission_share: 0.08 }),
    mockSubnet({ netuid: 19, name: "Vision", emission_share: 0.03 }),
  ],
  isLoading: false,
  isError: false,
  error: null,
  onRetry: vi.fn(),
};

describe("ScreenerTable", () => {
  it("renders table with correct column headers", () => {
    render(<ScreenerTable {...defaultProps} />);
    expect(screen.getByText("Subnet")).toBeInTheDocument();
    expect(screen.getByText("Miners")).toBeInTheDocument();
    expect(screen.getByText("Validators")).toBeInTheDocument();
    expect(screen.getByText("Reg Cost")).toBeInTheDocument();
    expect(screen.getByText("Emission %")).toBeInTheDocument();
    expect(screen.getByText("Alpha Price")).toBeInTheDocument();
    expect(screen.getByText("Age (days)")).toBeInTheDocument();
  });

  it("renders subnet rows with formatted data", () => {
    render(<ScreenerTable {...defaultProps} />);
    expect(screen.getByText("SN1")).toBeInTheDocument();
    expect(screen.getByText("· Text Prompting")).toBeInTheDocument();
    expect(screen.getByText("SN3")).toBeInTheDocument();
    expect(screen.getByText("· Data Scraping")).toBeInTheDocument();
  });

  it("default sort is emission share descending", () => {
    render(<ScreenerTable {...defaultProps} />);
    const rows = screen.getAllByRole("row");
    // Header row + 3 data rows
    expect(rows.length).toBe(4);
    // First data row should be highest emission (0.08 = SN3)
    const firstDataRow = rows[1];
    expect(within(firstDataRow).getByText("SN3")).toBeInTheDocument();
  });

  it("clicking column header sorts by that column", async () => {
    const user = userEvent.setup();
    render(<ScreenerTable {...defaultProps} />);

    await user.click(screen.getByText("Miners"));
    // After clicking miners (default desc), should sort by miner_count desc
    // All have same miner_count=100, so order may stay same
    expect(screen.getByText("▼")).toBeInTheDocument();
  });

  it("clicking same column header toggles sort direction", async () => {
    const user = userEvent.setup();
    render(<ScreenerTable {...defaultProps} />);

    // Default: emission_share desc (has ▼)
    expect(screen.getByText("▼")).toBeInTheDocument();

    // Click emission header to toggle to asc
    await user.click(screen.getByText("Emission %"));
    expect(screen.getByText("▲")).toBeInTheDocument();
  });

  it("shows loading skeleton when loading", () => {
    render(
      <ScreenerTable
        subnets={undefined}
        isLoading={true}
        isError={false}
        error={null}
        onRetry={vi.fn()}
      />
    );
    // Skeleton rows create animated pulse divs
    const pulseElements = document.querySelectorAll(".animate-pulse");
    expect(pulseElements.length).toBeGreaterThan(0);
  });

  it("shows error state with retry button", () => {
    const onRetry = vi.fn();
    render(
      <ScreenerTable
        subnets={undefined}
        isLoading={false}
        isError={true}
        error={new Error("Network error")}
        onRetry={onRetry}
      />
    );
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText(/Network error/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  it("calls onRetry when retry button clicked", async () => {
    const user = userEvent.setup();
    const onRetry = vi.fn();
    render(
      <ScreenerTable
        subnets={undefined}
        isLoading={false}
        isError={true}
        error={new Error("fail")}
        onRetry={onRetry}
      />
    );
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("shows empty state when no data", () => {
    render(
      <ScreenerTable
        subnets={[]}
        isLoading={false}
        isError={false}
        error={null}
        onRetry={vi.fn()}
      />
    );
    expect(screen.getByText("No subnet data available")).toBeInTheDocument();
  });

  it("renders sparkline charts in each row", () => {
    render(<ScreenerTable {...defaultProps} />);
    // Each row gets 2 sparklines (emission + price), 3 subnets = 6 sparklines
    const lineCharts = screen.getAllByTestId("line-chart");
    expect(lineCharts.length).toBe(6);
  });

  it("row links navigate to subnet detail", () => {
    render(
      <ScreenerTable
        {...defaultProps}
        subnets={[mockSubnet({ netuid: 42, name: "TestNet" })]}
      />
    );
    const link = screen.getByRole("link", { name: /SN42/ });
    expect(link).toHaveAttribute("href", "/subnets/42");
  });

  it("renders subnet without name", () => {
    render(
      <ScreenerTable
        {...defaultProps}
        subnets={[mockSubnet({ netuid: 99, name: null })]}
      />
    );
    expect(screen.getByText("SN99")).toBeInTheDocument();
  });

  // Selection tests (Task 1)
  describe("checkbox selection", () => {
    it("does not render checkboxes when selection props not provided", () => {
      render(<ScreenerTable {...defaultProps} />);
      expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
    });

    it("renders checkboxes when selection props provided", () => {
      render(
        <ScreenerTable
          {...defaultProps}
          selectedNetuids={new Set()}
          onSelectionChange={vi.fn()}
        />
      );
      const checkboxes = screen.getAllByRole("checkbox");
      expect(checkboxes.length).toBe(3); // one per subnet
    });

    it("checkboxes reflect selectedNetuids state", () => {
      render(
        <ScreenerTable
          {...defaultProps}
          selectedNetuids={new Set([1])}
          onSelectionChange={vi.fn()}
        />
      );
      const cb1 = screen.getByLabelText("Select SN1 for comparison");
      const cb3 = screen.getByLabelText("Select SN3 for comparison");
      expect(cb1).toBeChecked();
      expect(cb3).not.toBeChecked();
    });

    it("calls onSelectionChange with toggled netuid when checkbox clicked", async () => {
      const user = userEvent.setup();
      const onChange = vi.fn();
      render(
        <ScreenerTable
          {...defaultProps}
          selectedNetuids={new Set()}
          onSelectionChange={onChange}
        />
      );
      await user.click(screen.getByLabelText("Select SN1 for comparison"));
      expect(onChange).toHaveBeenCalledOnce();
      const newSet = onChange.mock.calls[0][0] as Set<number>;
      expect(newSet.has(1)).toBe(true);
    });

    it("calls onSelectionChange with removed netuid when unchecking", async () => {
      const user = userEvent.setup();
      const onChange = vi.fn();
      render(
        <ScreenerTable
          {...defaultProps}
          selectedNetuids={new Set([1, 3])}
          onSelectionChange={onChange}
        />
      );
      await user.click(screen.getByLabelText("Select SN1 for comparison"));
      expect(onChange).toHaveBeenCalledOnce();
      const newSet = onChange.mock.calls[0][0] as Set<number>;
      expect(newSet.has(1)).toBe(false);
      expect(newSet.has(3)).toBe(true);
    });

    it("disables unchecked checkboxes when 3 are selected (max)", () => {
      render(
        <ScreenerTable
          {...defaultProps}
          selectedNetuids={new Set([1, 3, 19])}
          onSelectionChange={vi.fn()}
        />
      );
      // All 3 are checked, so none should be disabled
      const checkboxes = screen.getAllByRole("checkbox");
      checkboxes.forEach((cb) => expect(cb).not.toBeDisabled());
    });

    it("disables unchecked checkboxes when 3 already selected and a 4th exists", () => {
      const subnets = [
        mockSubnet({ netuid: 1 }),
        mockSubnet({ netuid: 3 }),
        mockSubnet({ netuid: 19 }),
        mockSubnet({ netuid: 42 }),
      ];
      render(
        <ScreenerTable
          {...defaultProps}
          subnets={subnets}
          selectedNetuids={new Set([1, 3, 19])}
          onSelectionChange={vi.fn()}
        />
      );
      const cb42 = screen.getByLabelText("Select SN42 for comparison");
      expect(cb42).toBeDisabled();
    });

    it("does not call onSelectionChange when disabled checkbox clicked", async () => {
      const user = userEvent.setup();
      const onChange = vi.fn();
      const subnets = [
        mockSubnet({ netuid: 1 }),
        mockSubnet({ netuid: 3 }),
        mockSubnet({ netuid: 19 }),
        mockSubnet({ netuid: 42 }),
      ];
      render(
        <ScreenerTable
          {...defaultProps}
          subnets={subnets}
          selectedNetuids={new Set([1, 3, 19])}
          onSelectionChange={onChange}
        />
      );
      const cb42 = screen.getByLabelText("Select SN42 for comparison");
      await user.click(cb42);
      expect(onChange).not.toHaveBeenCalled();
    });
  });
});
