import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { ENGINE_URL } from "@/lib/constants";

async function forwardToEngine(
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

export async function POST(request: NextRequest) {
  const session = await auth();
  if (!session?.user?.id) {
    return NextResponse.json(
      { error: { type: "unauthorized", message: "Authentication required", code: 401 } },
      { status: 401 },
    );
  }

  if (session.user.premiumStatus !== "premium") {
    return NextResponse.json(
      { error: { type: "premium_required", message: "Premium subscription required to access predictions", code: 403 } },
      { status: 403 },
    );
  }

  const body = await request.text();
  return forwardToEngine(
    "/engine/predictions/yield",
    "POST",
    session.user.id,
    session.user.premiumStatus,
    body,
  );
}
