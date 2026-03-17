import { NextResponse } from "next/server";
import { ENGINE_URL } from "@/lib/constants";

/**
 * Forward a request to the Python engine with auth headers.
 * Shared by all prediction API routes.
 */
export async function forwardToEngine(
  enginePath: string,
  method: string,
  userId: string,
  premiumStatus: string,
  body?: string,
): Promise<NextResponse> {
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    "X-User-Id": userId,
    "X-Premium-Status": premiumStatus,
  };

  try {
    const res = await fetch(`${ENGINE_URL}${enginePath}`, {
      method,
      headers,
      body,
      signal: AbortSignal.timeout(30_000),
    });
    const data = await res.text();
    return new NextResponse(data, {
      status: res.status,
      headers: { "Content-Type": "application/json" },
    });
  } catch {
    return NextResponse.json(
      { error: { type: "engine_unavailable", message: "Engine is not reachable", code: 502 } },
      { status: 502 },
    );
  }
}
