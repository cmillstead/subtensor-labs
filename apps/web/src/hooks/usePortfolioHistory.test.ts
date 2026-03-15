import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { usePortfolioHistory } from "./usePortfolioHistory";
import type { ReactNode } from "react";
import { createElement } from "react";

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

const mockHistoryResponse = {
  data: {
    points: [
      { time: "2026-03-14T00:00:00+00:00", total_value_tao: 1200.0 },
      { time: "2026-03-14T12:00:00+00:00", total_value_tao: 1250.0 },
    ],
    data_start: null,
    time_range: "30d",
  },
  meta: {
    last_updated: "2026-03-14T12:00:00+00:00",
    cache_hit: false,
    compute_ms: 50,
  },
};

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("usePortfolioHistory", () => {
  it("does not fetch when addresses array is empty", () => {
    const fetchSpy = vi.spyOn(global, "fetch");
    const { result } = renderHook(() => usePortfolioHistory([], "30d"), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(false);
    expect(result.current.data).toBeUndefined();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("fetches history data when addresses are provided", async () => {
    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(mockHistoryResponse), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const { result } = renderHook(
      () =>
        usePortfolioHistory(
          ["5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty"],
          "30d",
        ),
      { wrapper: createWrapper() },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.data.points).toHaveLength(2);
    expect(result.current.data?.data.time_range).toBe("30d");
    expect(global.fetch).toHaveBeenCalledWith(
      "/api/proxy/portfolio/history",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          coldkey_addresses: [
            "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty",
          ],
          time_range: "30d",
        }),
      }),
    );
  });

  it("handles fetch error gracefully", async () => {
    vi.spyOn(global, "fetch").mockImplementation(() =>
      Promise.resolve(
        new Response(
          JSON.stringify({
            error: {
              type: "history_unavailable",
              message: "History service down",
              code: 502,
            },
          }),
          { status: 502, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );

    const { result } = renderHook(
      () =>
        usePortfolioHistory(
          ["5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty"],
          "7d",
        ),
      { wrapper: createWrapper() },
    );

    await waitFor(() => expect(result.current.isError).toBe(true), {
      timeout: 5000,
    });
    expect(result.current.error?.message).toContain("History service down");
  });
});
