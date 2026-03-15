import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { RangeInput } from "./RangeInput";

describe("RangeInput", () => {
  const defaultProps = {
    label: "Miner Count",
    minValue: null,
    maxValue: null,
    onMinChange: vi.fn(),
    onMaxChange: vi.fn(),
  };

  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders min and max inputs with correct labels", () => {
    render(<RangeInput {...defaultProps} />);
    expect(screen.getByLabelText("Miner Count minimum")).toBeInTheDocument();
    expect(screen.getByLabelText("Miner Count maximum")).toBeInTheDocument();
  });

  it("renders the filter label text", () => {
    render(<RangeInput {...defaultProps} />);
    expect(screen.getByText("Miner Count")).toBeInTheDocument();
  });

  it("shows suffix text when provided", () => {
    render(<RangeInput {...defaultProps} suffix="τ" />);
    expect(screen.getByText("(τ)")).toBeInTheDocument();
  });

  it("does not show suffix when not provided", () => {
    render(<RangeInput {...defaultProps} />);
    expect(screen.queryByText(/\(/)).not.toBeInTheDocument();
  });

  it("calls onMinChange after debounce when min input changes", async () => {
    const onMinChange = vi.fn();
    render(<RangeInput {...defaultProps} onMinChange={onMinChange} />);

    const minInput = screen.getByLabelText("Miner Count minimum");
    await userEvent.type(minInput, "50");

    // Should not be called before debounce
    expect(onMinChange).not.toHaveBeenCalled();

    // Advance timers past debounce
    vi.advanceTimersByTime(300);
    expect(onMinChange).toHaveBeenCalledWith(50);
  });

  it("calls onMaxChange after debounce when max input changes", async () => {
    const onMaxChange = vi.fn();
    render(<RangeInput {...defaultProps} onMaxChange={onMaxChange} />);

    const maxInput = screen.getByLabelText("Miner Count maximum");
    await userEvent.type(maxInput, "200");

    vi.advanceTimersByTime(300);
    expect(onMaxChange).toHaveBeenCalledWith(200);
  });

  it("calls onChange with null when input is cleared", async () => {
    const onMinChange = vi.fn();
    render(
      <RangeInput {...defaultProps} minValue={50} onMinChange={onMinChange} />,
    );

    const minInput = screen.getByLabelText("Miner Count minimum");
    await userEvent.clear(minInput);

    vi.advanceTimersByTime(300);
    expect(onMinChange).toHaveBeenCalledWith(null);
  });

  it("shows error styling when min > max", () => {
    render(<RangeInput {...defaultProps} minValue={100} maxValue={50} />);
    expect(screen.getByText("Min cannot exceed max")).toBeInTheDocument();
  });

  it("does not show error when min <= max", () => {
    render(<RangeInput {...defaultProps} minValue={50} maxValue={100} />);
    expect(
      screen.queryByText("Min cannot exceed max"),
    ).not.toBeInTheDocument();
  });

  it("does not show error when only min is set", () => {
    render(<RangeInput {...defaultProps} minValue={50} />);
    expect(
      screen.queryByText("Min cannot exceed max"),
    ).not.toBeInTheDocument();
  });

  it("has accessible labels and touch targets", () => {
    render(<RangeInput {...defaultProps} />);
    const minInput = screen.getByLabelText("Miner Count minimum");
    const maxInput = screen.getByLabelText("Miner Count maximum");

    expect(minInput).toHaveClass("min-h-[44px]");
    expect(maxInput).toHaveClass("min-h-[44px]");
  });

  it("shows placeholder text", () => {
    render(
      <RangeInput
        {...defaultProps}
        placeholderMin="0"
        placeholderMax="500"
      />,
    );
    expect(screen.getByPlaceholderText("0")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("500")).toBeInTheDocument();
  });
});
