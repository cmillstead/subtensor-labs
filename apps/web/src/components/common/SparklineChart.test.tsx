import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { SparklineChart } from "./SparklineChart";

// Mock Recharts to avoid SVG rendering issues in test environment
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

describe("SparklineChart", () => {
  it("renders with data", () => {
    render(<SparklineChart data={[1, 2, 3, 4, 5]} />);
    expect(screen.getByLabelText("Trend sparkline")).toBeInTheDocument();
    expect(screen.getByTestId("line-chart")).toBeInTheDocument();
  });

  it("renders empty state for no data", () => {
    render(<SparklineChart data={[]} />);
    expect(screen.getByLabelText("No trend data")).toBeInTheDocument();
  });

  it("uses default violet color for positive trend", () => {
    render(<SparklineChart data={[1, 2, 3]} />);
    const line = screen.getByTestId("line");
    expect(line.dataset.stroke).toBe("#8B5CF6");
  });

  it("uses rose color for negative trend", () => {
    render(<SparklineChart data={[5, 3, 1]} />);
    const line = screen.getByTestId("line");
    expect(line.dataset.stroke).toBe("#F43F5E");
  });

  it("uses custom colors when provided", () => {
    render(
      <SparklineChart data={[5, 3, 1]} color="#00FF00" negativeColor="#FF0000" />
    );
    const line = screen.getByTestId("line");
    expect(line.dataset.stroke).toBe("#FF0000");
  });

  it("applies default dimensions", () => {
    render(<SparklineChart data={[1, 2, 3]} />);
    const container = screen.getByLabelText("Trend sparkline");
    expect(container.style.width).toBe("80px");
    expect(container.style.height).toBe("24px");
  });

  it("applies custom dimensions", () => {
    render(<SparklineChart data={[1, 2, 3]} width={120} height={32} />);
    const container = screen.getByLabelText("Trend sparkline");
    expect(container.style.width).toBe("120px");
    expect(container.style.height).toBe("32px");
  });

  it("treats flat data as positive trend", () => {
    render(<SparklineChart data={[5, 5, 5]} />);
    const line = screen.getByTestId("line");
    expect(line.dataset.stroke).toBe("#8B5CF6");
  });

  it("handles single data point", () => {
    render(<SparklineChart data={[42]} />);
    expect(screen.getByLabelText("Trend sparkline")).toBeInTheDocument();
    const line = screen.getByTestId("line");
    expect(line.dataset.stroke).toBe("#8B5CF6");
  });
});
