import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TimeRangeSelector } from "./TimeRangeSelector";

describe("TimeRangeSelector", () => {
  it("renders three range buttons", () => {
    render(<TimeRangeSelector value="30d" onChange={() => {}} />);
    expect(screen.getByText("7D")).toBeInTheDocument();
    expect(screen.getByText("30D")).toBeInTheDocument();
    expect(screen.getByText("90D")).toBeInTheDocument();
  });

  it("marks the active button as checked", () => {
    render(<TimeRangeSelector value="7d" onChange={() => {}} />);
    expect(screen.getByText("7D")).toHaveAttribute("aria-checked", "true");
    expect(screen.getByText("30D")).toHaveAttribute("aria-checked", "false");
    expect(screen.getByText("90D")).toHaveAttribute("aria-checked", "false");
  });

  it("calls onChange with selected range", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<TimeRangeSelector value="30d" onChange={onChange} />);

    await user.click(screen.getByText("90D"));
    expect(onChange).toHaveBeenCalledWith("90d");
  });

  it("has radiogroup role with accessible label", () => {
    render(<TimeRangeSelector value="30d" onChange={() => {}} />);
    const group = screen.getByRole("radiogroup");
    expect(group).toHaveAttribute("aria-label", "Time range");
  });
});
