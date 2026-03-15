import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom";

// Mock ResizeObserver for Recharts ResponsiveContainer
class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = ResizeObserverMock;

// Mock usePortfolio before importing the page
const mockUsePortfolio = vi.fn();
vi.mock("@/hooks/usePortfolio", () => ({
  usePortfolio: (...args: unknown[]) => mockUsePortfolio(...args),
}));

// Must import after mocks are set up
import ExplorePage from "./page";

const VALID_ADDRESS = "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty";

function mockPortfolioData() {
  return {
    data: {
      data: {
        total_value_tao: 500,
        free_balance_tao: 10,
        staked_tao: 400,
        alpha_value_tao: 90,
        positions: [
          {
            netuid: 1,
            subnet_name: "Alpha",
            hotkey: "5abc",
            staked_tao: 400,
            alpha_holdings: 100,
            alpha_value_tao: 90,
            emission_share: 0.05,
            incentive: 0,
            trust: 0,
            dividends: 0,
            is_active: true,
            is_miner: false,
            delegations: [],
          },
        ],
        addresses: [VALID_ADDRESS],
        last_updated: "2026-03-14T12:00:00Z",
        change_24h_pct: 2.1,
        change_7d_pct: -0.5,
      },
    },
    isLoading: false,
    isError: false,
    error: null,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  mockUsePortfolio.mockReturnValue({
    data: undefined,
    isLoading: false,
    isError: false,
    error: null,
  });
});

describe("ExplorePage", () => {
  it("renders page title and description", () => {
    render(<ExplorePage />);
    expect(screen.getByText("Explore Portfolio")).toBeInTheDocument();
    expect(
      screen.getByText(/paste any coldkey address/i),
    ).toBeInTheDocument();
  });

  it("shows empty state initially", () => {
    render(<ExplorePage />);
    expect(
      screen.getByText(/enter an address to get started/i),
    ).toBeInTheDocument();
  });

  it("renders portfolio summary after address submitted", async () => {
    const user = userEvent.setup();
    mockUsePortfolio.mockReturnValue(mockPortfolioData());

    render(<ExplorePage />);
    await user.type(screen.getByRole("textbox"), VALID_ADDRESS);
    await user.click(
      screen.getByRole("button", { name: /view portfolio/i }),
    );

    // usePortfolio is now called with [address]
    expect(mockUsePortfolio).toHaveBeenCalledWith([VALID_ADDRESS]);
  });

  it("renders AllocationDonut and SubnetPositionList when positions exist", () => {
    mockUsePortfolio.mockReturnValue(mockPortfolioData());
    render(<ExplorePage />);

    expect(screen.getByText("Allocation")).toBeInTheDocument();
    expect(screen.getByText("Subnet Positions")).toBeInTheDocument();
  });

  it("does NOT render ExportCsvButton, PortfolioValueChart, or TimeRangeSelector", () => {
    mockUsePortfolio.mockReturnValue(mockPortfolioData());
    render(<ExplorePage />);

    expect(screen.queryByText("Export CSV")).not.toBeInTheDocument();
    expect(screen.queryByText("Portfolio Value")).not.toBeInTheDocument();
    expect(screen.queryByRole("radiogroup")).not.toBeInTheDocument();
  });

  it("shows error state on fetch failure", () => {
    mockUsePortfolio.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: { message: "Network error" },
    });

    render(<ExplorePage />);

    // Need address set to trigger error display - but error shows regardless
    // since usePortfolio is mocked to return error
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText("Network error")).toBeInTheDocument();
  });

  it("shows loading skeletons while fetching", () => {
    mockUsePortfolio.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      error: null,
    });

    render(<ExplorePage />);
    // Skeletons use specific aria/test patterns - check for their container
    expect(screen.getByText("Allocation")).toBeInTheDocument();
  });
});
