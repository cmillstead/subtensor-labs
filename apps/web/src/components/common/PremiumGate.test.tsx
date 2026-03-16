import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { PremiumGate } from "./PremiumGate";

const mockUseSession = vi.fn();

vi.mock("next-auth/react", () => ({
  useSession: () => mockUseSession(),
}));

function renderGate() {
  return render(
    <PremiumGate featureName="Advanced Filters">
      <div data-testid="child-content">Filter controls here</div>
    </PremiumGate>,
  );
}

describe("PremiumGate", () => {
  it("shows children without overlay when user is premium", () => {
    mockUseSession.mockReturnValue({
      data: { user: { premiumStatus: "premium" } },
      status: "authenticated",
    });

    renderGate();

    expect(screen.getByTestId("child-content")).toBeInTheDocument();
    expect(screen.queryByText("Upgrade to Premium")).not.toBeInTheDocument();
  });

  it("shows overlay with badge when user is free", () => {
    mockUseSession.mockReturnValue({
      data: { user: { premiumStatus: "free" } },
      status: "authenticated",
    });

    renderGate();

    expect(screen.getByText("Upgrade to Premium")).toBeInTheDocument();
    expect(screen.getByText("Premium")).toBeInTheDocument();
    expect(screen.getByText("Advanced Filters")).toBeInTheDocument();
  });

  it("shows overlay when user is not logged in", () => {
    mockUseSession.mockReturnValue({
      data: null,
      status: "unauthenticated",
    });

    renderGate();

    expect(screen.getByText("Upgrade to Premium")).toBeInTheDocument();
  });

  it("CTA button links to /premium", () => {
    mockUseSession.mockReturnValue({
      data: null,
      status: "unauthenticated",
    });

    renderGate();

    const link = screen.getByText("Upgrade to Premium");
    expect(link).toHaveAttribute("href", "/premium");
  });

  it("displays feature name in overlay", () => {
    mockUseSession.mockReturnValue({
      data: { user: { premiumStatus: "free" } },
      status: "authenticated",
    });

    renderGate();

    expect(screen.getByText("Advanced Filters")).toBeInTheDocument();
  });
});
