import { renderHook, waitFor, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement } from "react";
import { useSavedScreeners } from "./useSavedScreeners";

const SAMPLE_SCREENER = {
  id: 1,
  name: "Growth Filter",
  filters_json: {
    min_miners: 50,
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
    sort_by: "emission_share" as const,
    sort_direction: "desc" as const,
  },
  created_at: "2026-03-16T00:00:00Z",
  updated_at: "2026-03-16T00:00:00Z",
};

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  function Wrapper({ children }: { children: React.ReactNode }) {
    return createElement(QueryClientProvider, { client: queryClient }, children);
  }
  return Wrapper;
}

describe("useSavedScreeners", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("fetches saved screeners on mount", async () => {
    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify({ data: [SAMPLE_SCREENER] }), { status: 200 }),
    );

    const { result } = renderHook(() => useSavedScreeners(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.savedScreeners).toEqual([SAMPLE_SCREENER]);
    expect(global.fetch).toHaveBeenCalledWith("/api/screener/saved");
  });

  it("returns empty array when no saved screeners", async () => {
    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify({ data: [] }), { status: 200 }),
    );

    const { result } = renderHook(() => useSavedScreeners(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.savedScreeners).toEqual([]);
  });

  it("saveScreener posts and invalidates cache", async () => {
    const fetchSpy = vi.spyOn(global, "fetch");
    // Initial fetch
    fetchSpy.mockResolvedValueOnce(
      new Response(JSON.stringify({ data: [] }), { status: 200 }),
    );

    const { result } = renderHook(() => useSavedScreeners(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    // Save mutation
    fetchSpy.mockResolvedValueOnce(
      new Response(JSON.stringify({ data: SAMPLE_SCREENER }), { status: 201 }),
    );
    // Refetch after invalidation
    fetchSpy.mockResolvedValueOnce(
      new Response(JSON.stringify({ data: [SAMPLE_SCREENER] }), { status: 200 }),
    );

    await act(async () => {
      await result.current.saveScreener({
        name: "Growth Filter",
        filters_json: SAMPLE_SCREENER.filters_json,
      });
    });

    expect(fetchSpy).toHaveBeenCalledWith("/api/screener/saved", expect.objectContaining({
      method: "POST",
    }));
  });

  it("updateScreener puts and invalidates cache", async () => {
    const fetchSpy = vi.spyOn(global, "fetch");
    fetchSpy.mockResolvedValueOnce(
      new Response(JSON.stringify({ data: [SAMPLE_SCREENER] }), { status: 200 }),
    );

    const { result } = renderHook(() => useSavedScreeners(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    fetchSpy.mockResolvedValueOnce(
      new Response(JSON.stringify({ data: { ...SAMPLE_SCREENER, name: "Renamed" } }), { status: 200 }),
    );
    fetchSpy.mockResolvedValueOnce(
      new Response(JSON.stringify({ data: [{ ...SAMPLE_SCREENER, name: "Renamed" }] }), { status: 200 }),
    );

    await act(async () => {
      await result.current.updateScreener({ id: 1, name: "Renamed" });
    });

    expect(fetchSpy).toHaveBeenCalledWith("/api/screener/saved/1", expect.objectContaining({
      method: "PUT",
    }));
  });

  it("deleteScreener deletes and invalidates cache", async () => {
    const fetchSpy = vi.spyOn(global, "fetch");
    fetchSpy.mockResolvedValueOnce(
      new Response(JSON.stringify({ data: [SAMPLE_SCREENER] }), { status: 200 }),
    );

    const { result } = renderHook(() => useSavedScreeners(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    fetchSpy.mockResolvedValueOnce(
      new Response(JSON.stringify({ message: "Screener removed." }), { status: 200 }),
    );
    fetchSpy.mockResolvedValueOnce(
      new Response(JSON.stringify({ data: [] }), { status: 200 }),
    );

    await act(async () => {
      await result.current.deleteScreener(1);
    });

    expect(fetchSpy).toHaveBeenCalledWith("/api/screener/saved/1", expect.objectContaining({
      method: "DELETE",
    }));
  });

  it("handles error responses", async () => {
    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify({ error: { message: "Unauthorized" } }), { status: 401 }),
    );

    const { result } = renderHook(() => useSavedScreeners(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    // On fetch error, savedScreeners defaults to empty array
    expect(result.current.savedScreeners).toEqual([]);
  });
});
