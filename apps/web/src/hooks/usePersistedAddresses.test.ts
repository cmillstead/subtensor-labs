import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { usePersistedAddresses } from "./usePersistedAddresses";
import type { LabeledAddress } from "@/types";

const STORAGE_KEY = "subtensor-labs:addresses";

const mockStorage: Record<string, string> = {};
const localStorageMock = {
  getItem: vi.fn((key: string) => mockStorage[key] ?? null),
  setItem: vi.fn((key: string, value: string) => {
    mockStorage[key] = value;
  }),
  removeItem: vi.fn((key: string) => {
    delete mockStorage[key];
  }),
  clear: vi.fn(() => {
    Object.keys(mockStorage).forEach((key) => delete mockStorage[key]);
  }),
  get length() {
    return Object.keys(mockStorage).length;
  },
  key: vi.fn((_index: number) => null),
};

describe("usePersistedAddresses", () => {
  beforeEach(() => {
    Object.keys(mockStorage).forEach((key) => delete mockStorage[key]);
    vi.stubGlobal("localStorage", localStorageMock);
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns empty array when localStorage is empty", () => {
    const { result } = renderHook(() => usePersistedAddresses());
    expect(result.current.addresses).toEqual([]);
  });

  it("reads addresses from localStorage on mount", () => {
    const stored: LabeledAddress[] = [
      { address: "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty", label: "Main" },
    ];
    mockStorage[STORAGE_KEY] = JSON.stringify(stored);

    const { result } = renderHook(() => usePersistedAddresses());
    expect(result.current.addresses).toEqual(stored);
  });

  it("writes addresses to localStorage on change", () => {
    const { result } = renderHook(() => usePersistedAddresses());

    const newAddresses: LabeledAddress[] = [
      { address: "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty", label: "Wallet 1" },
    ];

    act(() => {
      result.current.setAddresses(newAddresses);
    });

    expect(localStorageMock.setItem).toHaveBeenCalledWith(
      STORAGE_KEY,
      JSON.stringify(newAddresses),
    );
    expect(result.current.addresses).toEqual(newAddresses);
  });

  it("recovers from invalid JSON in localStorage", () => {
    mockStorage[STORAGE_KEY] = "not valid json{{{";

    const { result } = renderHook(() => usePersistedAddresses());
    expect(result.current.addresses).toEqual([]);
  });

  it("recovers from non-array JSON in localStorage", () => {
    mockStorage[STORAGE_KEY] = JSON.stringify({ address: "foo" });

    const { result } = renderHook(() => usePersistedAddresses());
    expect(result.current.addresses).toEqual([]);
  });

  it("filters out invalid entries from localStorage", () => {
    const stored = [
      { address: "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty", label: "Valid" },
      { address: 123 }, // invalid — address not string
      null,
      "just a string",
      { address: "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY" }, // missing label
    ];
    mockStorage[STORAGE_KEY] = JSON.stringify(stored);

    const { result } = renderHook(() => usePersistedAddresses());
    expect(result.current.addresses).toEqual([
      { address: "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty", label: "Valid" },
    ]);
  });

  it("handles localStorage quota exceeded gracefully", () => {
    localStorageMock.setItem.mockImplementationOnce(() => {
      throw new DOMException("QuotaExceededError");
    });

    const { result } = renderHook(() => usePersistedAddresses());

    // Should not throw
    act(() => {
      result.current.setAddresses([
        { address: "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty", label: "Test" },
      ]);
    });

    // State should still be updated even though storage failed
    expect(result.current.addresses).toEqual([
      { address: "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty", label: "Test" },
    ]);
  });
});
