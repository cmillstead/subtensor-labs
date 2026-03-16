import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useAddresses } from "./useAddresses";

// Mock next-auth/react
const mockUseSession = vi.fn();
vi.mock("next-auth/react", () => ({
  useSession: () => mockUseSession(),
}));

// Mock usePersistedAddresses
const mockLocalAddresses = vi.fn();
const mockSetLocalAddresses = vi.fn();
vi.mock("./usePersistedAddresses", () => ({
  usePersistedAddresses: () => ({
    addresses: mockLocalAddresses(),
    setAddresses: mockSetLocalAddresses,
    hydrated: true,
  }),
}));

// Mock useServerAddresses
const mockServerAddresses = vi.fn();
const mockAddAddress = vi.fn();
const mockUpdateLabel = vi.fn();
const mockRemoveAddress = vi.fn();
vi.mock("./useServerAddresses", () => ({
  useServerAddresses: () => ({
    addresses: mockServerAddresses(),
    isLoading: false,
    addAddress: mockAddAddress,
    updateLabel: mockUpdateLabel,
    removeAddress: mockRemoveAddress,
    isAdding: false,
    isRemoving: false,
  }),
}));

describe("useAddresses", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockLocalAddresses.mockReturnValue([]);
    mockServerAddresses.mockReturnValue([]);
  });

  it("returns localStorage addresses when not authenticated", () => {
    mockUseSession.mockReturnValue({ data: null, status: "unauthenticated" });
    mockLocalAddresses.mockReturnValue([
      { address: "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty", label: "Local" },
    ]);

    const { result } = renderHook(() => useAddresses());

    expect(result.current.addresses).toHaveLength(1);
    expect(result.current.addresses[0].label).toBe("Local");
    expect(result.current.isAuthenticated).toBe(false);
  });

  it("returns server addresses when authenticated", () => {
    mockUseSession.mockReturnValue({
      data: { user: { id: "1", email: "test@example.com" } },
      status: "authenticated",
    });
    mockServerAddresses.mockReturnValue([
      {
        id: 1,
        coldkey_address: "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY",
        label: "Server Wallet",
        is_watch_only: false,
        created_at: "2026-01-01T00:00:00Z",
      },
    ]);

    const { result } = renderHook(() => useAddresses());

    expect(result.current.addresses).toHaveLength(1);
    expect(result.current.addresses[0].label).toBe("Server Wallet");
    expect(result.current.isAuthenticated).toBe(true);
  });

  it("calls localStorage setAddresses when anonymous", async () => {
    mockUseSession.mockReturnValue({ data: null, status: "unauthenticated" });
    mockLocalAddresses.mockReturnValue([]);

    const { result } = renderHook(() => useAddresses());

    act(() => {
      result.current.setAddresses([
        { address: "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty", label: "New" },
      ]);
    });

    expect(mockSetLocalAddresses).toHaveBeenCalledWith([
      { address: "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty", label: "New" },
    ]);
  });

  it("calls server addAddress when authenticated", async () => {
    mockUseSession.mockReturnValue({
      data: { user: { id: "1", email: "test@example.com" } },
      status: "authenticated",
    });
    mockServerAddresses.mockReturnValue([]);
    mockAddAddress.mockResolvedValue({});

    const { result } = renderHook(() => useAddresses());

    await act(async () => {
      await result.current.addAddress(
        "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty",
        "New Wallet",
      );
    });

    expect(mockAddAddress).toHaveBeenCalledWith({
      coldkey_address: "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty",
      label: "New Wallet",
    });
  });

  it("calls server removeAddress when authenticated", async () => {
    mockUseSession.mockReturnValue({
      data: { user: { id: "1", email: "test@example.com" } },
      status: "authenticated",
    });
    mockServerAddresses.mockReturnValue([
      {
        id: 5,
        coldkey_address: "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY",
        label: null,
        is_watch_only: false,
        created_at: "2026-01-01T00:00:00Z",
      },
    ]);
    mockRemoveAddress.mockResolvedValue({});

    const { result } = renderHook(() => useAddresses());

    await act(async () => {
      await result.current.removeAddress("5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY");
    });

    expect(mockRemoveAddress).toHaveBeenCalledWith(5);
  });
});
