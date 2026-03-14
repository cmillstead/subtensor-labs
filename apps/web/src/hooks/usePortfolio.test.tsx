import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { usePortfolio } from "./usePortfolio";
import type { ReactNode } from "react";

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

const mockPortfolioResponse = {
  data: {
    total_value_tao: 1234.56,
    free_balance_tao: 100,
    staked_tao: 900,
    alpha_value_tao: 234.56,
    positions: [],
    addresses: ["5D..."],
    last_updated: "2026-03-14T14:30:00Z",
  },
  meta: {
    last_updated: "2026-03-14T14:30:00Z",
    cache_hit: true,
    compute_ms: 120,
  },
};

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("usePortfolio", () => {
  it("does not fetch when addresses array is empty", () => {
    const fetchSpy = vi.spyOn(global, "fetch");
    const { result } = renderHook(() => usePortfolio([]), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(false);
    expect(result.current.data).toBeUndefined();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("fetches portfolio data when addresses are provided", async () => {
    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(mockPortfolioResponse), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const { result } = renderHook(
      () => usePortfolio(["5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty"]),
      { wrapper: createWrapper() },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.data.total_value_tao).toBe(1234.56);
    expect(global.fetch).toHaveBeenCalledWith(
      "/api/proxy/portfolio/aggregate",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          coldkey_addresses: [
            "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty",
          ],
        }),
      }),
    );
  });

  it("handles fetch error gracefully", async () => {
    // Mock all attempts (initial + retries) — each call needs a fresh Response
    vi.spyOn(global, "fetch").mockImplementation(() =>
      Promise.resolve(
        new Response(
          JSON.stringify({
            error: { type: "engine_unavailable", message: "Engine down", code: 502 },
          }),
          { status: 502, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    const { result } = renderHook(
      () => usePortfolio(["5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty"]),
      { wrapper },
    );

    await waitFor(() => expect(result.current.isError).toBe(true), {
      timeout: 5000,
    });
    expect(result.current.error?.message).toContain("Engine down");
  });
});
