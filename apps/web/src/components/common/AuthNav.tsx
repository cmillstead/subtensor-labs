"use client";

import { useSession, signOut } from "next-auth/react";
import Link from "next/link";

export function AuthNav() {
  const { data: session, status } = useSession();

  if (status === "loading") {
    return (
      <span className="text-sm text-text-muted">
        &hellip;
      </span>
    );
  }

  if (session?.user) {
    return (
      <div className="flex items-center gap-4 text-sm">
        <Link
          href="/settings"
          className="text-text-muted hover:text-text-primary transition-colors"
        >
          Settings
        </Link>
        <button
          onClick={() => signOut({ callbackUrl: "/" })}
          className="text-text-muted hover:text-text-primary transition-colors"
        >
          Sign Out
        </button>
      </div>
    );
  }

  return (
    <Link
      href="/auth/login"
      className="text-sm text-text-muted hover:text-text-primary transition-colors"
    >
      Sign In
    </Link>
  );
}
