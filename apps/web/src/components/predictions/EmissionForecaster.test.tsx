import { describe, it, expect, beforeAll } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  EmissionForecaster,
  EmissionForecasterSkeleton,
  filterChartData,
  buildMigrationChartData,
  formatDaysRemaining,
} from "./EmissionForecaster";
import type {
  SubnetEmissionForecast,
  HalvingImpact,
  SubnetStakingMigration,
} from "@/types";

// mock-ok: ResizeObserver is a DOM API not available in jsdom
beforeAll(() => {
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
});

function makeForecast(netuid: number, trend: "rising" | "falling" | "stable" = "rising"): SubnetEmissionForecast {
  return {
    netuid,
    subnet_name: `Subnet ${netuid}`,
    current_emission_share_pct: 5.0 + netuid,
    ema_trend: trend,
    momentum: trend === "rising" ? 0.05 : trend === "falling" ? -0.03 : 0.001,
    chart_data: Array.from({ length: 90 }, (_, i) => ({
      day: i + 1,
      emission_share_pct: 5.0 + i * 0.01,
      confidence_68_lower: 4.8 + i * 0.005,
      confidence_68_upper: 5.2 + i * 0.015,
      confidence_95_lower: 4.5 + i * 0.002,
      confidence_95_upper: 5.5 + i * 0.02,
    })),
  };
}

const halvingImpact: HalvingImpact = {
  blocks_remaining: 5_000_000,
  estimated_days_remaining: 694.4,
  current_emission_per_day_tao: 3600,
  post_halving_emission_per_day_tao: 1800,
  estimated_yield_impact_pct: -50,
  estimated_yield_impact_tao: -45.0,
};

const migrations: SubnetStakingMigration[] = [
  { netuid: 1, subnet_name: "SN1", net_tao_inflow_30d: 5000, avg_daily_inflow: 166.7, direction: "inflow" },
  { netuid: 3, subnet_name: "SN3", net_tao_inflow_30d: -3000, avg_daily_inflow: -100, direction: "outflow" },
  { netuid: 5, subnet_name: "SN5", net_tao_inflow_30d: 200, avg_daily_inflow: 6.7, direction: "inflow" },
];

const defaultProps = {
  subnetForecasts: [makeForecast(1), makeForecast(3, "falling")],
  halvingImpact,
  stakingMigration: migrations,
  caveat: "Based on trend extrapolation. Not financial advice.",
  subnetsAnalyzed: 2,
  subnetsSkipped: 1,
};

describe("EmissionForecaster", () => {
  it("renders caveat banner", () => {
    render(<EmissionForecaster {...defaultProps} />);
    expect(screen.getByText(/Not financial advice/)).toBeInTheDocument();
  });

  it("renders halving countdown card", () => {
    render(<EmissionForecaster {...defaultProps} />);
    expect(screen.getByText("Halving Countdown")).toBeInTheDocument();
    expect(screen.getByText("5,000,000")).toBeInTheDocument(); // blocks remaining
    expect(screen.getByText("-50%")).toBeInTheDocument(); // yield impact
  });

  it("renders emission trajectory section", () => {
    render(<EmissionForecaster {...defaultProps} />);
    expect(screen.getByText("Emission Trajectory")).toBeInTheDocument();
  });

  it("renders staking migration section", () => {
    render(<EmissionForecaster {...defaultProps} />);
    expect(screen.getByText("Staking Migration (30d)")).toBeInTheDocument();
  });

  it("renders subnet forecast table", () => {
    render(<EmissionForecaster {...defaultProps} />);
    expect(screen.getByText("Subnet Emission Forecasts")).toBeInTheDocument();
    // "Subnet 1" appears in both the select dropdown and the table
    expect(screen.getAllByText("Subnet 1").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Subnet 3").length).toBeGreaterThanOrEqual(1);
  });

  it("renders trend badges correctly", () => {
    render(<EmissionForecaster {...defaultProps} />);
    expect(screen.getByText("↑ Rising")).toBeInTheDocument();
    expect(screen.getByText("↓ Falling")).toBeInTheDocument();
  });

  it("renders subnets analyzed count", () => {
    render(<EmissionForecaster {...defaultProps} />);
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(screen.getByText("(1 skipped)")).toBeInTheDocument();
  });

  it("renders horizon selector with 30D/60D/90D options", () => {
    render(<EmissionForecaster {...defaultProps} />);
    expect(screen.getByText("30D")).toBeInTheDocument();
    expect(screen.getByText("60D")).toBeInTheDocument();
    expect(screen.getByText("90D")).toBeInTheDocument();
  });

  it("renders subnet selector when multiple forecasts", () => {
    render(<EmissionForecaster {...defaultProps} />);
    const select = screen.getByLabelText("Select subnet for emission chart");
    expect(select).toBeInTheDocument();
  });

  it("switches subnet on selector change", async () => {
    const user = userEvent.setup();
    render(<EmissionForecaster {...defaultProps} />);
    const select = screen.getByLabelText("Select subnet for emission chart") as HTMLSelectElement;
    await user.selectOptions(select, "3");
    expect(select.value).toBe("3");
  });

  it("switches horizon when clicking 60D button", async () => {
    const user = userEvent.setup();
    render(<EmissionForecaster {...defaultProps} />);
    const btn60 = screen.getByRole("radio", { name: "60D" });
    await user.click(btn60);
    expect(btn60).toHaveAttribute("aria-checked", "true");
  });

  it("handles empty forecasts gracefully", () => {
    render(
      <EmissionForecaster
        {...defaultProps}
        subnetForecasts={[]}
        stakingMigration={[]}
        subnetsAnalyzed={0}
        subnetsSkipped={0}
      />
    );
    expect(screen.getByText("Insufficient historical data for emission projection.")).toBeInTheDocument();
    expect(screen.getByText("No staking migration data available.")).toBeInTheDocument();
    expect(screen.getByText("No subnet forecast data available.")).toBeInTheDocument();
  });
});

describe("EmissionForecasterSkeleton", () => {
  it("renders with correct aria-label", () => {
    render(<EmissionForecasterSkeleton />);
    expect(screen.getByLabelText("Loading emission forecast")).toBeInTheDocument();
  });
});

describe("filterChartData", () => {
  const chartData = Array.from({ length: 90 }, (_, i) => ({
    day: i + 1,
    emission_share_pct: 5.0,
    confidence_68_lower: 4.5,
    confidence_68_upper: 5.5,
    confidence_95_lower: 4.0,
    confidence_95_upper: 6.0,
  }));

  it("filters to 30 days", () => {
    expect(filterChartData(chartData, 30)).toHaveLength(30);
  });

  it("filters to 60 days", () => {
    expect(filterChartData(chartData, 60)).toHaveLength(60);
  });

  it("filters to 90 days", () => {
    expect(filterChartData(chartData, 90)).toHaveLength(90);
  });
});

describe("buildMigrationChartData", () => {
  it("transforms migrations to chart data", () => {
    const result = buildMigrationChartData(migrations);
    expect(result).toHaveLength(3);
    expect(result[0]).toEqual({ netuid: 1, label: "SN1", value: 5000, direction: "inflow" });
    expect(result[1]).toEqual({ netuid: 3, label: "SN3", value: -3000, direction: "outflow" });
  });

  it("uses netuid as label when name is null", () => {
    const result = buildMigrationChartData([
      { netuid: 7, subnet_name: null, net_tao_inflow_30d: 100, avg_daily_inflow: 3.3, direction: "inflow" },
    ]);
    expect(result[0].label).toBe("SN7");
  });
});

describe("formatDaysRemaining", () => {
  it("formats days under a year", () => {
    expect(formatDaysRemaining(45)).toBe("~45d");
  });

  it("formats days over a year", () => {
    expect(formatDaysRemaining(694.4)).toBe("~1y 329d");
  });

  it("formats exact years", () => {
    expect(formatDaysRemaining(730)).toBe("~2y");
  });

  it("returns Imminent for negative days", () => {
    expect(formatDaysRemaining(-5)).toBe("Imminent");
  });

  it("returns Imminent for zero days", () => {
    expect(formatDaysRemaining(0)).toBe("Imminent");
  });
});
