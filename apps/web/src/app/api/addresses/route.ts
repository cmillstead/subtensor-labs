import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { ENGINE_URL } from "@/lib/constants";

async function forwardToEngine(
  enginePath: string,
  method: string,
  userId: string,
  body?: string,
): Promise<NextResponse> {
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    "X-User-Id": userId,
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

export async function GET() {
  const session = await auth();
  if (!session?.user?.id) {
    return NextResponse.json(
      { error: { type: "unauthorized", message: "Authentication required", code: 401 } },
      { status: 401 },
    );
  }

  return forwardToEngine(
    `/engine/users/${session.user.id}/addresses`,
    "GET",
    session.user.id,
  );
}

export async function POST(request: NextRequest) {
  const session = await auth();
  if (!session?.user?.id) {
    return NextResponse.json(
      { error: { type: "unauthorized", message: "Authentication required", code: 401 } },
      { status: 401 },
    );
  }

  const body = await request.text();
  return forwardToEngine(
    `/engine/users/${session.user.id}/addresses`,
    "POST",
    session.user.id,
    body,
  );
}
