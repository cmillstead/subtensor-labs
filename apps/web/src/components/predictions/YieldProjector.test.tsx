import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { YieldProjector, YieldProjectorSkeleton, prepareChartData, findHorizonProjection } from "./YieldProjector";
import type { YieldChartPoint, HorizonProjection, SubnetYieldProjection } from "@/types";

// Mock ResizeObserver for Recharts ResponsiveContainer
class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = ResizeObserverMock;

// --- Test data factories ---

function makeChartData(days: number = 90): YieldChartPoint[] {
  return Array.from({ length: days }, (_, i) => ({
    day: i + 1,
    projected_yield_tao: (i + 1) * 0.35,
    confidence_68_lower: (i + 1) * 0.27,
    confidence_68_upper: (i + 1) * 0.43,
    confidence_95_lower: (i + 1) * 0.17,
    confidence_95_upper: (i + 1) * 0.53,
  }));
}

function makeSubnetProjection(overrides: Partial<SubnetYieldProjection> = {}): SubnetYieldProjection {
  return {
    netuid: 1,
    subnet_name: "Alpha Subnet",
    current_stake_tao: 100,
    projected_yield_tao: 10.5,
    emission_trend_slope: 0.01,
    r_squared: 0.95,
    confidence_68_lower: 8.0,
    confidence_68_upper: 13.0,
    confidence_95_lower: 5.0,
    confidence_95_upper: 16.0,
    has_volatility_warning: false,
    ...overrides,
  };
}

function makeProjections(): HorizonProjection[] {
  return [30, 60, 90].map((horizon) => ({
    horizon_days: horizon,
    total_projected_yield_tao: 10.5 * (horizon / 30),
    total_confidence_68_lower: 8.0 * (horizon / 30),
    total_confidence_68_upper: 13.0 * (horizon / 30),
    total_confidence_95_lower: 5.0 * (horizon / 30),
    total_confidence_95_upper: 16.0 * (horizon / 30),
    subnet_projections: [makeSubnetProjection({ projected_yield_tao: 10.5 * (horizon / 30) })],
  }));
}

const CAVEAT = "Based on trend extrapolation. Not financial advice. Past emission trends do not guarantee future results.";

// --- Pure function tests ---

describe("prepareChartData", () => {
  it("filters chart data to selected horizon", () => {
    const data = makeChartData(90);
    const filtered = prepareChartData(data, 30);
    expect(filtered).toHaveLength(30);
    expect(filtered[0].day).toBe(1);
    expect(filtered[29].day).toBe(30);
  });

  it("returns all data when horizon matches", () => {
    const data = makeChartData(90);
    const filtered = prepareChartData(data, 90);
    expect(filtered).toHaveLength(90);
  });

  it("returns empty array for empty input", () => {
    const filtered = prepareChartData([], 30);
    expect(filtered).toHaveLength(0);
  });
});

describe("findHorizonProjection", () => {
  it("finds projection for matching horizon", () => {
    const projections = makeProjections();
    const result = findHorizonProjection(projections, 60);
    expect(result?.horizon_days).toBe(60);
  });

  it("returns undefined for non-matching horizon", () => {
    const projections = makeProjections();
    const result = findHorizonProjection(projections, 7 as never);
    expect(result).toBeUndefined();
  });
});

// --- Component tests ---

describe("YieldProjector", () => {
  const defaultProps = {
    chartData: makeChartData(),
    projections: makeProjections(),
    caveat: CAVEAT,
    totalStakedTao: 100,
    subnetsAnalyzed: 1,
    subnetsSkipped: 0,
  };

  it("renders caveat text", () => {
    render(<YieldProjector {...defaultProps} />);
    expect(screen.getByText(CAVEAT)).toBeInTheDocument();
  });

  it("renders total staked TAO", () => {
    render(<YieldProjector {...defaultProps} />);
    expect(screen.getByText(/Total Staked/)).toBeInTheDocument();
  });

  it("renders subnets analyzed count", () => {
    render(<YieldProjector {...defaultProps} />);
    expect(screen.getByText("1")).toBeInTheDocument();
  });

  it("renders subnet projection table", () => {
    render(<YieldProjector {...defaultProps} />);
    expect(screen.getByText("Alpha Subnet")).toBeInTheDocument();
  });

  it("renders volatility warning for young subnets", () => {
    const props = {
      ...defaultProps,
      projections: [
        {
          ...defaultProps.projections[0],
          subnet_projections: [
            makeSubnetProjection({ has_volatility_warning: true }),
          ],
        },
        ...defaultProps.projections.slice(1),
      ],
    };
    render(<YieldProjector {...props} />);
    expect(screen.getByText("Volatile")).toBeInTheDocument();
  });

  it("does not render volatility warning for mature subnets", () => {
    render(<YieldProjector {...defaultProps} />);
    expect(screen.queryByText("Volatile")).not.toBeInTheDocument();
  });

  it("shows horizon selector with 30D active by default", () => {
    render(<YieldProjector {...defaultProps} />);
    const radio30 = screen.getByRole("radio", { name: "30D" });
    expect(radio30).toHaveAttribute("aria-checked", "true");
  });

  it("switches horizon on click", async () => {
    const user = userEvent.setup();
    render(<YieldProjector {...defaultProps} />);

    const radio60 = screen.getByRole("radio", { name: "60D" });
    await user.click(radio60);
    expect(radio60).toHaveAttribute("aria-checked", "true");
  });

  it("shows skipped subnets count when present", () => {
    render(<YieldProjector {...defaultProps} subnetsSkipped={2} />);
    expect(screen.getByText("(2 skipped)")).toBeInTheDocument();
  });

  it("renders chart area", () => {
    render(<YieldProjector {...defaultProps} />);
    expect(
      screen.getByRole("img", { name: /Yield projection chart/ }),
    ).toBeInTheDocument();
  });

  it("shows empty message when no chart data", () => {
    render(<YieldProjector {...defaultProps} chartData={[]} />);
    expect(
      screen.getByText(/Insufficient historical data/),
    ).toBeInTheDocument();
  });
});

describe("YieldProjectorSkeleton", () => {
  it("renders loading skeleton", () => {
    render(<YieldProjectorSkeleton />);
    expect(
      screen.getByLabelText("Loading yield projections"),
    ).toBeInTheDocument();
  });
});
