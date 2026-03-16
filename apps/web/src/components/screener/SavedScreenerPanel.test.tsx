import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SavedScreenerPanel } from "./SavedScreenerPanel";
import type { ScreenerFilter, SavedScreener } from "@/types";

// Mock next-auth/react
const mockUseSession = vi.fn();
vi.mock("next-auth/react", () => ({
  useSession: () => mockUseSession(),
}));

// Mock useSavedScreeners
const mockSaveScreener = vi.fn();
const mockUpdateScreener = vi.fn();
const mockDeleteScreener = vi.fn();
const mockSavedScreeners = vi.fn<() => SavedScreener[]>(() => []);
const mockIsLoading = vi.fn(() => false);

vi.mock("@/hooks/useSavedScreeners", () => ({
  useSavedScreeners: () => ({
    savedScreeners: mockSavedScreeners(),
    isLoading: mockIsLoading(),
    saveScreener: mockSaveScreener,
    updateScreener: mockUpdateScreener,
    deleteScreener: mockDeleteScreener,
    isSaving: false,
    isDeleting: false,
  }),
}));

const EMPTY_FILTERS: ScreenerFilter = {
  min_miners: null,
  max_miners: null,
  min_validators: null,
  max_validators: null,
  min_registration_cost: null,
  max_registration_cost: null,
  min_emission_share: null,
  max_emission_share: null,
  min_alpha_price: null,
  max_alpha_price: null,
  min_subnet_age_days: null,
  max_subnet_age_days: null,
  min_alpha_price_change_24h: null,
  max_alpha_price_change_24h: null,
  min_alpha_price_change_7d: null,
  max_alpha_price_change_7d: null,
  min_alpha_price_change_30d: null,
  max_alpha_price_change_30d: null,
  min_alpha_market_cap: null,
  max_alpha_market_cap: null,
  min_net_tao_inflow: null,
  max_net_tao_inflow: null,
  min_fill_rate: null,
  max_fill_rate: null,
  min_owner_take_rate: null,
  max_owner_take_rate: null,
  immunity_active: null,
  sort_by: "emission_share",
  sort_direction: "desc",
};

const ACTIVE_FILTERS: ScreenerFilter = {
  ...EMPTY_FILTERS,
  min_miners: 50,
};

const SAMPLE_SCREENER: SavedScreener = {
  id: 1,
  name: "Growth Filter",
  filters_json: ACTIVE_FILTERS,
  created_at: "2026-03-16T00:00:00Z",
  updated_at: "2026-03-16T00:00:00Z",
};

function premiumSession() {
  return {
    data: { user: { id: "1", premiumStatus: "premium" } },
    status: "authenticated" as const,
  };
}

function freeSession() {
  return {
    data: { user: { id: "1", premiumStatus: "free" } },
    status: "authenticated" as const,
  };
}

function unauthenticatedSession() {
  return { data: null, status: "unauthenticated" as const };
}

describe("SavedScreenerPanel", () => {
  const mockOnLoadScreener = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockSavedScreeners.mockReturnValue([]);
    mockIsLoading.mockReturnValue(false);
    mockSaveScreener.mockResolvedValue({});
    mockUpdateScreener.mockResolvedValue({});
    mockDeleteScreener.mockResolvedValue({});
  });

  it("shows sign-in prompt for unauthenticated users", () => {
    mockUseSession.mockReturnValue(unauthenticatedSession());
    render(
      <SavedScreenerPanel
        filters={EMPTY_FILTERS}
        onLoadScreener={mockOnLoadScreener}
        activeFilterCount={0}
      />,
    );
    expect(
      screen.getByText("Sign in to save your screener configurations."),
    ).toBeInTheDocument();
  });

  it("shows PremiumGate for non-premium users", () => {
    mockUseSession.mockReturnValue(freeSession());
    render(
      <SavedScreenerPanel
        filters={EMPTY_FILTERS}
        onLoadScreener={mockOnLoadScreener}
        activeFilterCount={0}
      />,
    );
    expect(screen.getByText("Upgrade to Premium")).toBeInTheDocument();
  });

  it("shows empty state when no saved screeners", () => {
    mockUseSession.mockReturnValue(premiumSession());
    render(
      <SavedScreenerPanel
        filters={EMPTY_FILTERS}
        onLoadScreener={mockOnLoadScreener}
        activeFilterCount={0}
      />,
    );
    expect(
      screen.getByText(
        "No saved screeners yet. Apply filters and save your first configuration.",
      ),
    ).toBeInTheDocument();
  });

  it("disables Save Screener button when no active filters", () => {
    mockUseSession.mockReturnValue(premiumSession());
    render(
      <SavedScreenerPanel
        filters={EMPTY_FILTERS}
        onLoadScreener={mockOnLoadScreener}
        activeFilterCount={0}
      />,
    );
    const saveButton = screen.getByRole("button", { name: "Save Screener" });
    expect(saveButton).toBeDisabled();
  });

  it("enables Save Screener button when filters are active", () => {
    mockUseSession.mockReturnValue(premiumSession());
    render(
      <SavedScreenerPanel
        filters={ACTIVE_FILTERS}
        onLoadScreener={mockOnLoadScreener}
        activeFilterCount={1}
      />,
    );
    const saveButton = screen.getByRole("button", { name: "Save Screener" });
    expect(saveButton).not.toBeDisabled();
  });

  it("save flow: click save → enter name → confirm → calls saveScreener", async () => {
    const user = userEvent.setup();
    mockUseSession.mockReturnValue(premiumSession());
    render(
      <SavedScreenerPanel
        filters={ACTIVE_FILTERS}
        onLoadScreener={mockOnLoadScreener}
        activeFilterCount={1}
      />,
    );

    // Click Save Screener
    await user.click(screen.getByRole("button", { name: "Save Screener" }));

    // Enter name
    const input = screen.getByLabelText("Screener name");
    await user.type(input, "My Growth Filter");

    // Click Confirm
    await user.click(screen.getByRole("button", { name: "Confirm" }));

    expect(mockSaveScreener).toHaveBeenCalledWith({
      name: "My Growth Filter",
      filters_json: ACTIVE_FILTERS,
    });
  });

  it("shows 'Saved' feedback after successful save", async () => {
    const user = userEvent.setup();
    mockUseSession.mockReturnValue(premiumSession());
    render(
      <SavedScreenerPanel
        filters={ACTIVE_FILTERS}
        onLoadScreener={mockOnLoadScreener}
        activeFilterCount={1}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Save Screener" }));
    const input = screen.getByLabelText("Screener name");
    await user.type(input, "Test");
    await user.click(screen.getByRole("button", { name: "Confirm" }));

    await waitFor(() => {
      expect(screen.getByText("Saved")).toBeInTheDocument();
    });
  });

  it("renders saved screeners list", () => {
    mockUseSession.mockReturnValue(premiumSession());
    mockSavedScreeners.mockReturnValue([SAMPLE_SCREENER]);
    render(
      <SavedScreenerPanel
        filters={EMPTY_FILTERS}
        onLoadScreener={mockOnLoadScreener}
        activeFilterCount={0}
      />,
    );
    expect(screen.getByText("Growth Filter")).toBeInTheDocument();
  });

  it("load screener: click item → calls onLoadScreener with correct filters", async () => {
    const user = userEvent.setup();
    mockUseSession.mockReturnValue(premiumSession());
    mockSavedScreeners.mockReturnValue([SAMPLE_SCREENER]);
    render(
      <SavedScreenerPanel
        filters={EMPTY_FILTERS}
        onLoadScreener={mockOnLoadScreener}
        activeFilterCount={0}
      />,
    );

    await user.click(screen.getByText("Growth Filter"));
    expect(mockOnLoadScreener).toHaveBeenCalledWith(SAMPLE_SCREENER.filters_json);
  });

  it("delete screener: click delete → calls deleteScreener", async () => {
    const user = userEvent.setup();
    mockUseSession.mockReturnValue(premiumSession());
    mockSavedScreeners.mockReturnValue([SAMPLE_SCREENER]);
    render(
      <SavedScreenerPanel
        filters={EMPTY_FILTERS}
        onLoadScreener={mockOnLoadScreener}
        activeFilterCount={0}
      />,
    );

    await user.click(screen.getByLabelText("Delete Growth Filter"));
    expect(mockDeleteScreener).toHaveBeenCalledWith(1);
  });

  it("save via Enter key", async () => {
    const user = userEvent.setup();
    mockUseSession.mockReturnValue(premiumSession());
    render(
      <SavedScreenerPanel
        filters={ACTIVE_FILTERS}
        onLoadScreener={mockOnLoadScreener}
        activeFilterCount={1}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Save Screener" }));
    const input = screen.getByLabelText("Screener name");
    await user.type(input, "Enter Key Test{Enter}");

    expect(mockSaveScreener).toHaveBeenCalledWith({
      name: "Enter Key Test",
      filters_json: ACTIVE_FILTERS,
    });
  });

  it("cancel save mode via Escape key", async () => {
    const user = userEvent.setup();
    mockUseSession.mockReturnValue(premiumSession());
    render(
      <SavedScreenerPanel
        filters={ACTIVE_FILTERS}
        onLoadScreener={mockOnLoadScreener}
        activeFilterCount={1}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Save Screener" }));
    const input = screen.getByLabelText("Screener name");
    expect(input).toBeInTheDocument();

    // Focus the input first (autoFocus was removed for a11y), then press Escape
    await user.click(input);
    await user.keyboard("{Escape}");
    expect(screen.queryByLabelText("Screener name")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save Screener" })).toBeInTheDocument();
  });
});
