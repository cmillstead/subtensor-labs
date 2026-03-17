import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { SessionProvider } from "next-auth/react";
import PredictionsPage from "./page";

// Mock next-auth
vi.mock("next-auth/react", async () => {
  const actual = await vi.importActual("next-auth/react");
  return {
    ...actual,
    useSession: vi.fn(() => ({
      data: {
        user: { id: "1", premiumStatus: "premium" },
      },
      status: "authenticated",
    })),
  };
});

// Mock useAddresses hook
vi.mock("@/hooks/useAddresses", () => ({
  useAddresses: vi.fn(() => ({
    addresses: [],
    hydrated: true,
    setAddresses: vi.fn(),
    addAddress: vi.fn(),
    removeAddress: vi.fn(),
    updateLabel: vi.fn(),
  })),
}));

// Mock usePredictions hook
vi.mock("@/hooks/usePredictions", () => ({
  useYieldProjection: vi.fn(() => ({
    data: null,
    isLoading: false,
    isError: false,
    error: null,
  })),
}));

describe("PredictionsPage", () => {
  it("renders page title", () => {
    render(
      <SessionProvider>
        <PredictionsPage />
      </SessionProvider>,
    );
    expect(screen.getByText("Predictions")).toBeInTheDocument();
  });

  it("renders tab navigation", () => {
    render(
      <SessionProvider>
        <PredictionsPage />
      </SessionProvider>,
    );
    expect(screen.getByRole("tab", { name: /Yield Projector/ })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Scenario Calculator/ })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Emission Forecast/ })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Alpha Trends/ })).toBeInTheDocument();
  });

  it("shows empty state when no addresses", () => {
    render(
      <SessionProvider>
        <PredictionsPage />
      </SessionProvider>,
    );
    expect(screen.getByText("No addresses connected")).toBeInTheDocument();
  });

  it("disables future tabs", () => {
    render(
      <SessionProvider>
        <PredictionsPage />
      </SessionProvider>,
    );
    const scenarioTab = screen.getByRole("tab", { name: /Scenario Calculator/ });
    expect(scenarioTab).toBeDisabled();
  });

  it("yield projector tab is selected by default", () => {
    render(
      <SessionProvider>
        <PredictionsPage />
      </SessionProvider>,
    );
    const yieldTab = screen.getByRole("tab", { name: /Yield Projector/ });
    expect(yieldTab).toHaveAttribute("aria-selected", "true");
  });
});
