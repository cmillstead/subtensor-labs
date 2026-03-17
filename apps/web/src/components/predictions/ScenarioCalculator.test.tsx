import { vi, describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  ScenarioCalculator,
  ScenarioCalculatorSkeleton,
  buildComparisonChartData,
  getBestLabels,
} from "./ScenarioCalculator";
import type { ScenarioComparisonResult } from "@/types";

// Mock ResizeObserver for Recharts ResponsiveContainer
class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = ResizeObserverMock;

// mock-ok: useScenarioCalculation wraps useMutation calling a remote backend API with no local sandbox
vi.mock("@/hooks/usePredictions", () => ({
  useScenarioCalculation: () => ({
    mutate: vi.fn(),
    isPending: false,
    isError: false,
    error: null,
    data: null,
  }),
}));

// --- Test data factories ---

function makeComparison(
  overrides: Partial<ScenarioComparisonResult> = {},
): ScenarioComparisonResult {
  return {
    horizon_days: 90,
    baseline: {
      label: "Current",
      total_projected_yield_tao: 10.5,
      total_confidence_68_lower: 8.0,
      total_confidence_68_upper: 13.0,
      total_confidence_95_lower: 5.0,
      total_confidence_95_upper: 16.0,
      total_alpha_exposure_tao: 500,
      hhi: 3400,
      yield_delta_tao: 0,
      yield_delta_pct: 0,
      subnet_allocations: [],
    },
    scenarios: [
      {
        label: "All-in SN1",
        total_projected_yield_tao: 14.2,
        total_confidence_68_lower: 10.0,
        total_confidence_68_upper: 18.0,
        total_confidence_95_lower: 6.0,
        total_confidence_95_upper: 22.0,
        total_alpha_exposure_tao: 1000,
        hhi: 10000,
        yield_delta_tao: 3.7,
        yield_delta_pct: 35.2,
        subnet_allocations: [],
      },
      {
        label: "Diversify",
        total_projected_yield_tao: 11.8,
        total_confidence_68_lower: 9.0,
        total_confidence_68_upper: 14.0,
        total_confidence_95_lower: 7.0,
        total_confidence_95_upper: 17.0,
        total_alpha_exposure_tao: 250,
        hhi: 2500,
        yield_delta_tao: 1.3,
        yield_delta_pct: 12.4,
        subnet_allocations: [],
      },
    ],
    best_yield_index: 0,
    best_diversification_index: 1,
    ...overrides,
  };
}

const CAVEAT =
  "Based on trend extrapolation. Not financial advice. Past emission trends do not guarantee future results.";

const defaultProps = {
  addresses: ["5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty"],
  currentStakes: { 1: 500, 3: 300, 19: 200 } as Record<number, number>,
  availableNetuids: [1, 3, 19, 64],
};

// --- Pure function tests ---

describe("buildComparisonChartData", () => {
  it("returns correct entries for baseline + scenarios", () => {
    const comparison = makeComparison();
    const data = buildComparisonChartData(comparison);

    expect(data).toHaveLength(3);
    expect(data[0].name).toBe("Current");
    expect(data[0].yield).toBe(10.5);
    expect(data[1].name).toBe("All-in SN1");
    expect(data[1].yield).toBe(14.2);
    expect(data[2].name).toBe("Diversify");
    expect(data[2].yield).toBe(11.8);
  });

  it("uses correct colors", () => {
    const comparison = makeComparison();
    const data = buildComparisonChartData(comparison);

    expect(data[0].color).toBe("#8B5CF6"); // baseline violet
    expect(data[1].color).toBe("#F43F5E"); // first scenario rose
    expect(data[2].color).toBe("#10B981"); // second scenario emerald
  });
});

describe("getBestLabels", () => {
  it("returns correct best yield label", () => {
    const comparison = makeComparison();
    const labels = getBestLabels(comparison);
    expect(labels.bestYield).toBe("All-in SN1");
  });

  it("returns correct best diversification label", () => {
    const comparison = makeComparison();
    const labels = getBestLabels(comparison);
    expect(labels.bestDiversification).toBe("Diversify");
  });

  it("returns null when index points to missing scenario", () => {
    const comparison = makeComparison({
      best_yield_index: 5,
      best_diversification_index: 10,
    });
    const labels = getBestLabels(comparison);
    expect(labels.bestYield).toBeNull();
    expect(labels.bestDiversification).toBeNull();
  });
});

// --- Component tests ---

describe("ScenarioCalculatorSkeleton", () => {
  it("renders with aria-label", () => {
    render(<ScenarioCalculatorSkeleton />);
    expect(
      screen.getByLabelText("Loading scenario calculator"),
    ).toBeInTheDocument();
  });
});

describe("ScenarioCalculator", () => {
  it("renders current allocation section", () => {
    render(<ScenarioCalculator {...defaultProps} />);
    expect(screen.getByText("Current Allocation")).toBeInTheDocument();
    // SN labels appear in both allocation chips and scenario selects;
    // just verify the section heading and total are present
    expect(screen.getByText(/Total:/)).toBeInTheDocument();
  });

  it("renders scenario builder section", () => {
    render(<ScenarioCalculator {...defaultProps} />);
    expect(screen.getByText("Scenarios")).toBeInTheDocument();
  });

  it("renders horizon selector with 30D/60D/90D", () => {
    render(<ScenarioCalculator {...defaultProps} />);
    expect(screen.getByRole("radio", { name: "30D" })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "60D" })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "90D" })).toBeInTheDocument();
  });

  it("has 90D selected by default", () => {
    render(<ScenarioCalculator {...defaultProps} />);
    const radio90 = screen.getByRole("radio", { name: "90D" });
    expect(radio90).toHaveAttribute("aria-checked", "true");
  });

  it("renders Calculate button", () => {
    render(<ScenarioCalculator {...defaultProps} />);
    expect(
      screen.getByRole("button", { name: "Calculate" }),
    ).toBeInTheDocument();
  });

  it("renders Add Scenario button", () => {
    render(<ScenarioCalculator {...defaultProps} />);
    expect(
      screen.getByRole("button", { name: /Add Scenario/ }),
    ).toBeInTheDocument();
  });

  it("shows caveat banner", () => {
    render(<ScenarioCalculator {...defaultProps} />);
    expect(screen.getByText(CAVEAT)).toBeInTheDocument();
  });

  it("clicking Add Scenario adds another scenario card", async () => {
    const user = userEvent.setup();
    render(<ScenarioCalculator {...defaultProps} />);

    // Initially 1 scenario card with "Scenario 1 name" label
    expect(screen.getAllByLabelText(/Scenario \d+ name/)).toHaveLength(1);

    const addBtn = screen.getByRole("button", { name: /Add Scenario/ });
    await user.click(addBtn);
    expect(screen.getAllByLabelText(/Scenario \d+ name/)).toHaveLength(2);

    await user.click(addBtn);
    expect(screen.getAllByLabelText(/Scenario \d+ name/)).toHaveLength(3);
  });

  it("hides Add Scenario button when 3 scenarios exist", async () => {
    const user = userEvent.setup();
    render(<ScenarioCalculator {...defaultProps} />);

    const addBtn = screen.getByRole("button", { name: /Add Scenario/ });
    await user.click(addBtn);
    await user.click(addBtn);

    // Now at 3 scenarios, button should be gone
    expect(
      screen.queryByRole("button", { name: /Add Scenario/ }),
    ).not.toBeInTheDocument();
  });
});
