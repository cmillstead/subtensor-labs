import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { PremiumBadge } from "./PremiumBadge";

describe("PremiumBadge", () => {
  it("renders badge with 'Premium' text", () => {
    render(<PremiumBadge />);
    expect(screen.getByText("Premium")).toBeInTheDocument();
  });

  it("has gradient background style", () => {
    render(<PremiumBadge />);
    const badge = screen.getByText("Premium");
    expect(badge.style.background).toContain("linear-gradient");
  });
});
