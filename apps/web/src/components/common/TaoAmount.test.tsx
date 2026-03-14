import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { TaoAmount } from "./TaoAmount";

describe("TaoAmount", () => {
  it("renders TAO amount with tau symbol and comma formatting", () => {
    render(<TaoAmount value={1234.56} />);
    expect(screen.getByText(/τ/)).toBeInTheDocument();
    expect(screen.getByText(/1,234\.56/)).toBeInTheDocument();
  });

  it("renders zero value", () => {
    render(<TaoAmount value={0} />);
    expect(screen.getByText(/τ/)).toBeInTheDocument();
    expect(screen.getByText(/0\.00/)).toBeInTheDocument();
  });

  it("abbreviates large values (thousands)", () => {
    render(<TaoAmount value={1200} abbreviate />);
    expect(screen.getByText(/1\.2K/)).toBeInTheDocument();
  });

  it("abbreviates large values (millions)", () => {
    render(<TaoAmount value={1500000} abbreviate />);
    expect(screen.getByText(/1\.5M/)).toBeInTheDocument();
  });

  it("renders small values with full precision", () => {
    render(<TaoAmount value={0.12} />);
    expect(screen.getByText(/0\.12/)).toBeInTheDocument();
  });

  it("renders USD conversion when showUsd is true", () => {
    render(<TaoAmount value={100} showUsd usdPrice={238.57} />);
    expect(screen.getByText(/\$23,857/)).toBeInTheDocument();
  });

  it("applies large variant class", () => {
    const { container } = render(<TaoAmount value={100} size="large" />);
    expect(container.firstChild).toHaveClass("text-3xl");
  });

  it("applies medium variant class", () => {
    const { container } = render(<TaoAmount value={100} size="medium" />);
    expect(container.firstChild).toHaveClass("text-xl");
  });

  it("applies small variant class", () => {
    const { container } = render(<TaoAmount value={100} size="small" />);
    expect(container.firstChild).toHaveClass("text-sm");
  });

  it("uses monospace font", () => {
    const { container } = render(<TaoAmount value={100} />);
    expect(container.firstChild).toHaveClass("font-mono");
  });

  it("has accessible aria-label", () => {
    render(<TaoAmount value={1234.56} />);
    expect(screen.getByLabelText(/1,234\.56 TAO/)).toBeInTheDocument();
  });
});
