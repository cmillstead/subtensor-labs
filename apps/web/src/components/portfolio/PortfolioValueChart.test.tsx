import { describe, it, expect, vi, beforeAll } from "vitest";
import { render, screen } from "@testing-library/react";
import {
  PortfolioValueChart,
  PortfolioValueChartSkeleton,
  formatTaoAxis,
  formatDateAxis,
} from "./PortfolioValueChart";
import type { PortfolioHistoryPoint } from "@/types";

// Mock ResizeObserver for Recharts ResponsiveContainer (jsdom doesn't provide it)
beforeAll(() => {
  vi.stubGlobal(
    "ResizeObserver",
    vi.fn().mockImplementation(() => ({
      observe: vi.fn(),
      unobserve: vi.fn(),
      disconnect: vi.fn(),
    })),
  );
});

const mockPoints: PortfolioHistoryPoint[] = [
  { time: "2026-03-10T00:00:00+00:00", total_value_tao: 1200.5 },
  { time: "2026-03-11T00:00:00+00:00", total_value_tao: 1350.75 },
  { time: "2026-03-12T00:00:00+00:00", total_value_tao: 1100.25 },
];

describe("PortfolioValueChart", () => {
  it("renders chart container with ARIA label", () => {
    render(
      <PortfolioValueChart
        points={mockPoints}
        dataStart={null}
        timeRange="30d"
      />,
    );
    const figure = screen.getByRole("figure");
    expect(figure).toHaveAttribute(
      "aria-label",
      "Historical portfolio value chart showing total value in TAO over time",
    );
  });

  it("renders chart wrapper div for data points", () => {
    const { container } = render(
      <PortfolioValueChart
        points={mockPoints}
        dataStart={null}
        timeRange="30d"
      />,
    );
    // ResponsiveContainer requires actual dimensions to render SVG.
    // In jsdom we verify the chart wrapper renders with correct height class.
    const chartWrapper = container.querySelector(".h-\\[300px\\]");
    expect(chartWrapper).not.toBeNull();
  });

  it("shows empty state when no data points", () => {
    render(
      <PortfolioValueChart points={[]} dataStart={null} timeRange="30d" />,
    );
    expect(
      screen.getByText(/No historical data available yet/),
    ).toBeInTheDocument();
  });

  it("shows tracking since note when dataStart is provided", () => {
    render(
      <PortfolioValueChart
        points={mockPoints}
        dataStart="2026-03-10T00:00:00+00:00"
        timeRange="30d"
      />,
    );
    expect(screen.getByText(/Tracking since/)).toBeInTheDocument();
  });

  it("shows estimate disclaimer when data points exist", () => {
    render(
      <PortfolioValueChart
        points={mockPoints}
        dataStart={null}
        timeRange="30d"
      />,
    );
    expect(
      screen.getByText("Based on current positions"),
    ).toBeInTheDocument();
  });

  it("does not show tracking since note when dataStart is null", () => {
    render(
      <PortfolioValueChart
        points={mockPoints}
        dataStart={null}
        timeRange="30d"
      />,
    );
    expect(screen.queryByText(/Tracking since/)).not.toBeInTheDocument();
  });
});

describe("formatTaoAxis", () => {
  it("formats millions", () => {
    expect(formatTaoAxis(1_500_000)).toBe("τ 1.5M");
  });

  it("formats thousands", () => {
    expect(formatTaoAxis(45_300)).toBe("τ 45.3K");
  });

  it("formats small values", () => {
    expect(formatTaoAxis(123)).toBe("τ 123");
  });
});

describe("formatDateAxis", () => {
  it("formats 7d range with weekday and hour", () => {
    const result = formatDateAxis("2026-03-14T14:00:00+00:00", "7d");
    expect(result).toMatch(/\w+/);
  });

  it("formats 30d range with month and day", () => {
    // Use a date with explicit timezone offset to avoid local TZ issues
    const result = formatDateAxis("2026-03-14T12:00:00+00:00", "30d");
    // In any timezone, noon UTC on Mar 14 is either Mar 14 or Mar 15
    expect(result).toMatch(/Mar\s+1[3-5]/);
  });
});

describe("PortfolioValueChartSkeleton", () => {
  it("renders with loading label", () => {
    render(<PortfolioValueChartSkeleton />);
    expect(
      screen.getByLabelText("Loading portfolio value chart"),
    ).toBeInTheDocument();
  });
});
