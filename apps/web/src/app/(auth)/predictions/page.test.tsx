import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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

// mock-ok: hooks fetch from Bittensor backend API with no local sandbox
vi.mock("@/hooks/usePredictions", () => ({
  useYieldProjection: vi.fn(() => ({
    data: null,
    isLoading: false,
    isError: false,
    error: null,
  })),
}));

// mock-ok: hook fetches from Bittensor backend API with no local sandbox
vi.mock("@/hooks/usePortfolio", () => ({
  usePortfolio: vi.fn(() => ({
    data: {
      data: {
        positions: [
          { netuid: 1, staked_tao: 100 },
          { netuid: 3, staked_tao: 50 },
        ],
      },
    },
    isLoading: false,
    isError: false,
  })),
}));

// mock-ok: page-level test verifies tab integration, not component internals
vi.mock("@/components/predictions/ScenarioCalculator", () => ({
  ScenarioCalculator: () => (
    <div data-testid="scenario-calculator">Scenario Calculator Content</div>
  ),
  ScenarioCalculatorSkeleton: () => <div>Loading scenario...</div>,
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
    const emissionTab = screen.getByRole("tab", { name: /Emission Forecast/ });
    expect(emissionTab).toBeDisabled();
    const alphaTab = screen.getByRole("tab", { name: /Alpha Trends/ });
    expect(alphaTab).toBeDisabled();
  });

  it("scenario calculator tab is enabled", () => {
    render(
      <SessionProvider>
        <PredictionsPage />
      </SessionProvider>,
    );
    const scenarioTab = screen.getByRole("tab", { name: /Scenario Calculator/ });
    expect(scenarioTab).toBeEnabled();
    expect(scenarioTab).not.toHaveTextContent("Soon");
  });

  it("clicking scenario calculator tab renders scenario content", async () => {
    // Override useAddresses to provide addresses so ScenarioCalculator renders
    const { useAddresses } = await import("@/hooks/useAddresses");
    vi.mocked(useAddresses).mockReturnValue({
      addresses: [{ address: "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty", label: "Main" }],
      hydrated: true,
      setAddresses: vi.fn(),
      addAddress: vi.fn(),
      removeAddress: vi.fn(),
      updateLabel: vi.fn(),
    } as ReturnType<typeof useAddresses>);

    const user = userEvent.setup();
    render(
      <SessionProvider>
        <PredictionsPage />
      </SessionProvider>,
    );
    const scenarioTab = screen.getByRole("tab", { name: /Scenario Calculator/ });
    await user.click(scenarioTab);
    expect(scenarioTab).toHaveAttribute("aria-selected", "true");
    expect(screen.getByTestId("scenario-calculator")).toBeInTheDocument();

    // Restore default mock for subsequent tests
    vi.mocked(useAddresses).mockReturnValue({
      addresses: [],
      hydrated: true,
      setAddresses: vi.fn(),
      addAddress: vi.fn(),
      removeAddress: vi.fn(),
      updateLabel: vi.fn(),
    } as ReturnType<typeof useAddresses>);
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
