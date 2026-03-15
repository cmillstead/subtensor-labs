import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom";
import { ExportCsvButton } from "./ExportCsvButton";
import type { PortfolioResult } from "@/types";

function makeResult(
  overrides: Partial<PortfolioResult> = {},
): PortfolioResult {
  return {
    total_value_tao: 200,
    free_balance_tao: 10,
    staked_tao: 150,
    alpha_value_tao: 40,
    positions: [
      {
        netuid: 1,
        subnet_name: "Alpha",
        hotkey: "5abc",
        staked_tao: 100,
        alpha_holdings: 50,
        alpha_value_tao: 25,
        emission_share: 0.03,
        incentive: 0,
        trust: 0,
        dividends: 0,
        is_active: true,
        is_miner: false,
        delegations: [],
      },
    ],
    addresses: ["5abc"],
    last_updated: "2026-03-14T12:00:00Z",
    change_24h_pct: null,
    change_7d_pct: null,
    ...overrides,
  };
}

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("ExportCsvButton", () => {
  it("renders Export CSV button", () => {
    render(<ExportCsvButton data={makeResult()} isLoading={false} />);
    expect(
      screen.getByRole("button", { name: /export csv/i }),
    ).toBeInTheDocument();
  });

  it("is disabled when isLoading is true", () => {
    render(<ExportCsvButton data={makeResult()} isLoading={true} />);
    expect(screen.getByRole("button")).toBeDisabled();
  });

  it("is disabled when data is undefined", () => {
    render(<ExportCsvButton data={undefined} isLoading={false} />);
    expect(screen.getByRole("button")).toBeDisabled();
  });

  it("is disabled when positions array is empty", () => {
    render(
      <ExportCsvButton
        data={makeResult({ positions: [] })}
        isLoading={false}
      />,
    );
    expect(screen.getByRole("button")).toBeDisabled();
  });

  it("is enabled when valid data is provided", () => {
    render(<ExportCsvButton data={makeResult()} isLoading={false} />);
    expect(screen.getByRole("button")).toBeEnabled();
  });

  it("triggers CSV download on click", async () => {
    const user = userEvent.setup();
    const mockUrl = "blob:http://localhost/fake";
    URL.createObjectURL = vi.fn(() => mockUrl);
    URL.revokeObjectURL = vi.fn();

    // Track anchors appended to body
    const originalAppendChild = document.body.appendChild.bind(document.body);
    const appendedNodes: Node[] = [];
    vi.spyOn(document.body, "appendChild").mockImplementation((node) => {
      appendedNodes.push(node);
      return originalAppendChild(node);
    });

    render(<ExportCsvButton data={makeResult()} isLoading={false} />);
    await user.click(screen.getByRole("button"));

    expect(URL.createObjectURL).toHaveBeenCalledOnce();
    const anchor = appendedNodes.find(
      (n) => n instanceof HTMLAnchorElement,
    ) as HTMLAnchorElement;
    expect(anchor).toBeTruthy();
    expect(anchor.download).toMatch(
      /^subtensor-labs-portfolio-\d{4}-\d{2}-\d{2}\.csv$/,
    );
    expect(URL.revokeObjectURL).toHaveBeenCalledWith(mockUrl);
  });

  it("shows tooltip explaining disabled state", () => {
    render(<ExportCsvButton data={undefined} isLoading={false} />);
    expect(screen.getByRole("button")).toHaveAttribute("title");
  });
});
