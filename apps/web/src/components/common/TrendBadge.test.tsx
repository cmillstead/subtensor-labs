import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { TrendBadge } from "./TrendBadge";

describe("TrendBadge", () => {
  it("renders positive trend with up arrow and emerald color", () => {
    const { container } = render(<TrendBadge value={6.92} />);
    expect(screen.getByText(/↑/)).toBeInTheDocument();
    expect(screen.getByText(/\+6\.9%/)).toBeInTheDocument();
    expect(container.firstChild).toHaveClass("text-success");
  });

  it("renders negative trend with down arrow and rose color", () => {
    const { container } = render(<TrendBadge value={-3.14} />);
    expect(screen.getByText(/↓/)).toBeInTheDocument();
    expect(screen.getByText(/3\.1%/)).toBeInTheDocument();
    expect(container.firstChild).toHaveClass("text-error");
  });

  it("renders neutral trend with right arrow and gray color", () => {
    const { container } = render(<TrendBadge value={0} />);
    expect(screen.getByText(/→/)).toBeInTheDocument();
    expect(screen.getByText(/0\.0%/)).toBeInTheDocument();
    expect(container.firstChild).toHaveClass("text-text-muted");
  });

  it("renders null value as neutral", () => {
    const { container } = render(<TrendBadge value={null} />);
    expect(screen.getByText(/—/)).toBeInTheDocument();
    expect(container.firstChild).toHaveClass("text-text-muted");
  });

  it("uses monospace font", () => {
    const { container } = render(<TrendBadge value={5} />);
    expect(container.firstChild).toHaveClass("font-mono");
  });

  it("has accessible aria-label", () => {
    render(<TrendBadge value={6.92} />);
    expect(screen.getByLabelText(/up 6\.9%/i)).toBeInTheDocument();
  });
});
