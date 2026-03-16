"use client";

import { useSession } from "next-auth/react";
import type { ReactNode } from "react";
import { PremiumBadge } from "./PremiumBadge";

interface PremiumGateProps {
  children: ReactNode;
  featureName: string;
}

export function PremiumGate({ children, featureName }: PremiumGateProps) {
  const { data: session } = useSession();
  const isPremium = session?.user?.premiumStatus === "premium";

  if (isPremium) {
    return <>{children}</>;
  }

  return (
    <div className="relative">
      <div className="pointer-events-none select-none blur-[2px]">
        {children}
      </div>
      <div className="absolute inset-0 flex flex-col items-center justify-center rounded-lg bg-zinc-900/80">
        <PremiumBadge />
        <p className="mt-2 text-sm font-medium text-zinc-200">
          {featureName}
        </p>
        <p className="mt-1 text-xs text-zinc-400">
          Unlock advanced screening tools
        </p>
        <a
          href="/premium"
          className="mt-3 inline-flex items-center rounded-md px-3 py-1.5 text-sm font-medium text-white"
          style={{
            background: "linear-gradient(135deg, #8B5CF6, #EC4899)",
          }}
        >
          Upgrade to Premium
        </a>
      </div>
    </div>
  );
}
