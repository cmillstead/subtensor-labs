import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom";
import { ScreenerCSVExport } from "./ScreenerCSVExport";
import type { ScreenerSubnet } from "@/types";

function makeSubnet(overrides: Partial<ScreenerSubnet> = {}): ScreenerSubnet {
  return {
    netuid: 1,
    name: "Text Prompting",
    miner_count: 120,
    validator_count: 24,
    registration_cost: 1000.5,
    emission_share: 0.05,
    alpha_price: 2.3,
    alpha_market_cap: 50000,
    fill_rate: 0.95,
    owner_take_rate: 0.18,
    tao_reserves: 100000,
    alpha_reserves: 500000,
    subnet_age_days: 365,
    sparkline_emission_7d: [0.04, 0.045, 0.05],
    sparkline_price_7d: [2.1, 2.2, 2.3],
    ...overrides,
  };
}

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("ScreenerCSVExport", () => {
  it("renders Export CSV button", () => {
    render(<ScreenerCSVExport subnets={[makeSubnet()]} isLoading={false} />);
    expect(
      screen.getByRole("button", { name: /export csv/i }),
    ).toBeInTheDocument();
  });

  it("is disabled when isLoading is true", () => {
    render(<ScreenerCSVExport subnets={[makeSubnet()]} isLoading={true} />);
    expect(screen.getByRole("button")).toBeDisabled();
  });

  it("is disabled when subnets is undefined", () => {
    render(<ScreenerCSVExport subnets={undefined} isLoading={false} />);
    expect(screen.getByRole("button")).toBeDisabled();
  });

  it("is disabled when subnets array is empty", () => {
    render(<ScreenerCSVExport subnets={[]} isLoading={false} />);
    expect(screen.getByRole("button")).toBeDisabled();
  });

  it("is enabled when valid subnets are provided", () => {
    render(<ScreenerCSVExport subnets={[makeSubnet()]} isLoading={false} />);
    expect(screen.getByRole("button")).toBeEnabled();
  });

  it("triggers CSV download on click", async () => {
    const user = userEvent.setup();
    const mockUrl = "blob:http://localhost/fake";
    URL.createObjectURL = vi.fn(() => mockUrl);
    URL.revokeObjectURL = vi.fn();

    const originalAppendChild = document.body.appendChild.bind(document.body);
    const appendedNodes: Node[] = [];
    vi.spyOn(document.body, "appendChild").mockImplementation((node) => {
      appendedNodes.push(node);
      return originalAppendChild(node);
    });

    render(<ScreenerCSVExport subnets={[makeSubnet()]} isLoading={false} />);
    await user.click(screen.getByRole("button"));

    expect(URL.createObjectURL).toHaveBeenCalledOnce();
    const anchor = appendedNodes.find(
      (n) => n instanceof HTMLAnchorElement,
    ) as HTMLAnchorElement;
    expect(anchor).toBeTruthy();
    expect(anchor.download).toMatch(
      /^subtensor-labs-screener-\d{4}-\d{2}-\d{2}\.csv$/,
    );
    expect(URL.revokeObjectURL).toHaveBeenCalledWith(mockUrl);
  });

  it("shows tooltip for loading state", () => {
    render(<ScreenerCSVExport subnets={undefined} isLoading={true} />);
    expect(screen.getByRole("button")).toHaveAttribute(
      "title",
      "Loading screener data…",
    );
  });

  it("shows tooltip for empty data state", () => {
    render(<ScreenerCSVExport subnets={[]} isLoading={false} />);
    expect(screen.getByRole("button")).toHaveAttribute(
      "title",
      "No subnet data to export",
    );
  });
});
