import { describe, it, expect, vi, beforeEach } from "vitest";
import { engineFetch, EngineClientError } from "@/lib/engine-client";

describe("engineFetch", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("returns parsed JSON on success", async () => {
    const mockData = { data: { status: "ok" } };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockData),
      }),
    );

    const result = await engineFetch("/health");
    expect(result).toEqual(mockData);
  });

  it("throws EngineClientError on network failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new Error("ECONNREFUSED")),
    );

    await expect(engineFetch("/health")).rejects.toThrow(EngineClientError);
    await expect(engineFetch("/health")).rejects.toMatchObject({
      type: "network_error",
      statusCode: 0,
    });
  });

  it("throws EngineClientError with engine error details on non-OK response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        json: () =>
          Promise.resolve({
            error: { type: "not_found", message: "Route not found" },
          }),
      }),
    );

    await expect(engineFetch("/missing")).rejects.toMatchObject({
      type: "not_found",
      statusCode: 404,
    });
  });

  it("throws EngineClientError when response is not valid JSON", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.reject(new SyntaxError("Unexpected token")),
      }),
    );

    await expect(engineFetch("/health")).rejects.toMatchObject({
      type: "parse_error",
      statusCode: 200,
    });
  });

  it("falls back to generic error when response body is not JSON", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        json: () => Promise.reject(new SyntaxError("not JSON")),
      }),
    );

    await expect(engineFetch("/crash")).rejects.toMatchObject({
      type: "engine_error",
      statusCode: 500,
      message: "Engine returned 500",
    });
  });
});
