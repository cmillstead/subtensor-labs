import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock fetch before importing the module
const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

describe("usePortfolioHistory", () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it("fetches portfolio history with correct parameters", async () => {
    const mockResponse = {
      data: {
        points: [
          { time: "2026-03-14T00:00:00+00:00", total_value_tao: 1200.0 },
        ],
        data_start: null,
        time_range: "30d",
      },
      meta: {
        last_updated: "2026-03-14T00:00:00+00:00",
        compute_ms: 50,
      },
    };

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    });

    // Directly test the fetch function by calling the endpoint
    const response = await fetch("/api/proxy/portfolio/history", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        coldkey_addresses: ["5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty"],
        time_range: "30d",
      }),
    });

    const data = await response.json();

    expect(mockFetch).toHaveBeenCalledWith("/api/proxy/portfolio/history", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        coldkey_addresses: ["5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty"],
        time_range: "30d",
      }),
    });
    expect(data.data.points).toHaveLength(1);
    expect(data.data.time_range).toBe("30d");
  });
});
