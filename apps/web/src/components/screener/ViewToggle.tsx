"use client";

type ScreenerView = "table" | "chart";

interface ViewToggleProps {
  view: ScreenerView;
  onViewChange: (view: ScreenerView) => void;
}

function ViewToggle({ view, onViewChange }: ViewToggleProps) {
  return (
    <div className="flex gap-1 rounded-lg bg-elevated p-1">
      <button
        type="button"
        className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
          view === "table"
            ? "bg-surface text-text-primary shadow-sm"
            : "text-text-secondary hover:text-text-primary"
        }`}
        aria-pressed={view === "table"}
        onClick={() => onViewChange("table")}
      >
        {/* Grid/table icon */}
        <svg
          width="14"
          height="14"
          viewBox="0 0 14 14"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        >
          <rect x="1" y="1" width="5" height="5" rx="0.5" stroke="currentColor" strokeWidth="1.2" />
          <rect x="8" y="1" width="5" height="5" rx="0.5" stroke="currentColor" strokeWidth="1.2" />
          <rect x="1" y="8" width="5" height="5" rx="0.5" stroke="currentColor" strokeWidth="1.2" />
          <rect x="8" y="8" width="5" height="5" rx="0.5" stroke="currentColor" strokeWidth="1.2" />
        </svg>
        Table
      </button>
      <button
        type="button"
        className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
          view === "chart"
            ? "bg-surface text-text-primary shadow-sm"
            : "text-text-secondary hover:text-text-primary"
        }`}
        aria-pressed={view === "chart"}
        onClick={() => onViewChange("chart")}
      >
        {/* Scatter/bubble chart icon */}
        <svg
          width="14"
          height="14"
          viewBox="0 0 14 14"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        >
          <circle cx="4" cy="5" r="2" stroke="currentColor" strokeWidth="1.2" />
          <circle cx="9" cy="3" r="1.5" stroke="currentColor" strokeWidth="1.2" />
          <circle cx="10" cy="9" r="2.5" stroke="currentColor" strokeWidth="1.2" />
          <circle cx="4" cy="10" r="1" stroke="currentColor" strokeWidth="1.2" />
        </svg>
        Chart
      </button>
    </div>
  );
}

export { ViewToggle };
export type { ScreenerView, ViewToggleProps };
