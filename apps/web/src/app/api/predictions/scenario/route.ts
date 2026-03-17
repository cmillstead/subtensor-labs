import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { forwardToEngine } from "@/lib/engine-proxy";

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
    "/engine/predictions/scenario",
    "POST",
    session.user.id,
    session.user.premiumStatus,
    body,
  );
}
