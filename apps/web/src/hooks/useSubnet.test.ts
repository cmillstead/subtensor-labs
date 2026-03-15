import { renderHook, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement } from "react";
import { useSubnet } from "./useSubnet";

const mockResponse = {
  data: {
    detail: {
      netuid: 1,
      name: "Text Prompting",
      miner_count: 100,
      validator_count: 50,
      registration_cost: 1.5,
      emission_share: 0.05,
      alpha_price: 0.12,
      alpha_market_cap: 1200,
      tao_reserves: 500,
      alpha_reserves: 4000,
      fill_rate: 0.78,
      owner_take_rate: 0.18,
      subnet_age_days: 120,
      description: null,
    },
    history: [],
    miners: [],
    validators: [],
  },
  meta: {
    last_updated: "2026-03-15T00:00:00Z",
    cache_hit: false,
    compute_ms: 50,
  },
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

describe("useSubnet", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("fetches subnet data from correct URL", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(mockResponse), { status: 200 }),
    );

    const { result } = renderHook(() => useSubnet(1, "30d"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(fetchSpy).toHaveBeenCalledWith("/api/proxy/subnets/1?time_range=30d");
  });

  it("fetches with 7d time range", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(mockResponse), { status: 200 }),
    );

    const { result } = renderHook(() => useSubnet(42, "7d"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(fetchSpy).toHaveBeenCalledWith("/api/proxy/subnets/42?time_range=7d");
  });

  it("returns data on success", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(mockResponse), { status: 200 }),
    );

    const { result } = renderHook(() => useSubnet(1, "30d"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.data.detail.netuid).toBe(1);
    expect(result.current.data?.data.detail.name).toBe("Text Prompting");
  });

  it("handles error responses", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response("Not found", { status: 404 }),
    );

    const { result } = renderHook(() => useSubnet(999, "30d"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error).toBeDefined();
  });
});
