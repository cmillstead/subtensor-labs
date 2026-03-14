import { NextRequest, NextResponse } from "next/server";

const ENGINE_URL = process.env.ENGINE_URL || "http://localhost:8000";

/** Allowed engine path prefixes — reject anything outside this list. */
const ALLOWED_PREFIXES = [
  "/engine/health",
  "/engine/portfolio",
  "/engine/screener",
  "/engine/subnets",
  "/engine/predictions",
  "/engine/alerts",
];

function isAllowed(path: string): boolean {
  return ALLOWED_PREFIXES.some((prefix) => path.startsWith(prefix));
}

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
  const headers = new Headers(request.headers);
  headers.delete("host");

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

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params;
  return proxyToEngine(request, `/engine/${path.join("/")}`);
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params;
  return proxyToEngine(request, `/engine/${path.join("/")}`);
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params;
  return proxyToEngine(request, `/engine/${path.join("/")}`);
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params;
  return proxyToEngine(request, `/engine/${path.join("/")}`);
}
