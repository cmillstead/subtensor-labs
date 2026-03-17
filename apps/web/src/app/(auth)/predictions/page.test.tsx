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
  useEmissionForecast: vi.fn(() => ({
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

// mock-ok: page-level test verifies tab integration, not component internals
vi.mock("@/components/predictions/EmissionForecaster", () => ({
  EmissionForecaster: () => (
    <div data-testid="emission-forecaster">Emission Forecast Content</div>
  ),
  EmissionForecasterSkeleton: () => <div>Loading emission...</div>,
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
    // Emission Forecast tab is now enabled (story 6.3)
    const emissionTab = screen.getByRole("tab", { name: /Emission Forecast/ });
    expect(emissionTab).toBeEnabled();
    // Alpha Trends tab is still disabled
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

  it("clicking emission forecast tab renders emission content", async () => {
    const { useAddresses } = await import("@/hooks/useAddresses");
    vi.mocked(useAddresses).mockReturnValue({
      addresses: [{ address: "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty", label: "Main" }],
      hydrated: true,
      setAddresses: vi.fn(),
      addAddress: vi.fn(),
      removeAddress: vi.fn(),
      updateLabel: vi.fn(),
    } as ReturnType<typeof useAddresses>);

    // Override useEmissionForecast to return data so the component renders
    const { useEmissionForecast } = await import("@/hooks/usePredictions");
    vi.mocked(useEmissionForecast).mockReturnValue({
      data: {
        data: {
          subnet_forecasts: [],
          halving_impact: {} as never,
          staking_migration: [],
          caveat: "Test caveat",
          subnets_analyzed: 0,
          subnets_skipped: 0,
        },
      },
      isLoading: false,
      isError: false,
      error: null,
    } as ReturnType<typeof useEmissionForecast>);

    const user = userEvent.setup();
    render(
      <SessionProvider>
        <PredictionsPage />
      </SessionProvider>,
    );
    const emissionTab = screen.getByRole("tab", { name: /Emission Forecast/ });
    await user.click(emissionTab);
    expect(emissionTab).toHaveAttribute("aria-selected", "true");
    expect(screen.getByTestId("emission-forecaster")).toBeInTheDocument();

    // Restore default mocks
    vi.mocked(useAddresses).mockReturnValue({
      addresses: [],
      hydrated: true,
      setAddresses: vi.fn(),
      addAddress: vi.fn(),
      removeAddress: vi.fn(),
      updateLabel: vi.fn(),
    } as ReturnType<typeof useAddresses>);
    vi.mocked(useEmissionForecast).mockReturnValue({
      data: null,
      isLoading: false,
      isError: false,
      error: null,
    } as ReturnType<typeof useEmissionForecast>);
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
