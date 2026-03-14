import { NextRequest, NextResponse } from "next/server";
import { ENGINE_URL } from "@/lib/constants";
import { isAllowed } from "@/lib/proxy-allowlist";

/** Headers safe to forward to the engine. All others are stripped. */
const FORWARDED_HEADERS = ["content-type", "accept", "x-request-id"];

async function proxyToEngine(
  request: NextRequest,
  enginePath: string,
): Promise<NextResponse> {
  if (!isAllowed(enginePath)) {
    return NextResponse.json(
      { error: { type: "forbidden", message: "Path not allowed", code: 403 } },
      { status: 403 },
    );
  }

  const url = `${ENGINE_URL}${enginePath}`;
  // Only forward safe headers — strip Cookie, Authorization, etc.
  const headers = new Headers();
  for (const name of FORWARDED_HEADERS) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }

  try {
    const response = await fetch(url, {
      method: request.method,
      headers,
      body: request.method !== "GET" ? await request.text() : undefined,
    });

    const body = await response.text();
    return new NextResponse(body, {
      status: response.status,
      headers: { "Content-Type": response.headers.get("Content-Type") || "application/json" },
    });
  } catch {
    return NextResponse.json(
      { error: { type: "engine_unavailable", message: "Engine is not reachable", code: 502 } },
      { status: 502 },
    );
  }
}

function makeHandler() {
  return async (
    request: NextRequest,
    { params }: { params: Promise<{ path: string[] }> },
  ) => {
    const { path } = await params;
    return proxyToEngine(request, `/engine/${path.join("/")}`);
  };
}

export const GET = makeHandler();
export const POST = makeHandler();
export const PUT = makeHandler();
export const DELETE = makeHandler();
