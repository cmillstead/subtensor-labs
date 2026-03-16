import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ViewToggle } from "./ViewToggle";

describe("ViewToggle", () => {
  it("renders table and chart buttons", () => {
    render(<ViewToggle view="table" onViewChange={vi.fn()} />);
    expect(screen.getByText("Table")).toBeInTheDocument();
    expect(screen.getByText("Chart")).toBeInTheDocument();
  });

  it("marks table as active when view is table", () => {
    render(<ViewToggle view="table" onViewChange={vi.fn()} />);
    const tableBtn = screen.getByText("Table").closest("button")!;
    const chartBtn = screen.getByText("Chart").closest("button")!;
    expect(tableBtn).toHaveAttribute("aria-pressed", "true");
    expect(chartBtn).toHaveAttribute("aria-pressed", "false");
  });

  it("marks chart as active when view is chart", () => {
    render(<ViewToggle view="chart" onViewChange={vi.fn()} />);
    const tableBtn = screen.getByText("Table").closest("button")!;
    const chartBtn = screen.getByText("Chart").closest("button")!;
    expect(tableBtn).toHaveAttribute("aria-pressed", "false");
    expect(chartBtn).toHaveAttribute("aria-pressed", "true");
  });

  it("calls onViewChange with 'chart' when chart button clicked", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<ViewToggle view="table" onViewChange={onChange} />);
    await user.click(screen.getByText("Chart"));
    expect(onChange).toHaveBeenCalledWith("chart");
  });

  it("calls onViewChange with 'table' when table button clicked", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<ViewToggle view="chart" onViewChange={onChange} />);
    await user.click(screen.getByText("Table"));
    expect(onChange).toHaveBeenCalledWith("table");
  });

  it("is keyboard accessible via Enter key", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<ViewToggle view="table" onViewChange={onChange} />);
    const chartBtn = screen.getByText("Chart").closest("button")!;
    chartBtn.focus();
    await user.keyboard("{Enter}");
    expect(onChange).toHaveBeenCalledWith("chart");
  });

  it("is keyboard accessible via Space key", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<ViewToggle view="table" onViewChange={onChange} />);
    const chartBtn = screen.getByText("Chart").closest("button")!;
    chartBtn.focus();
    await user.keyboard(" ");
    expect(onChange).toHaveBeenCalledWith("chart");
  });
});
