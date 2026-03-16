"use client";

export function PremiumBadge() {
  return (
    <span
      className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium text-white"
      style={{
        background: "linear-gradient(135deg, #8B5CF6, #EC4899)",
      }}
    >
      Premium
    </span>
  );
}
