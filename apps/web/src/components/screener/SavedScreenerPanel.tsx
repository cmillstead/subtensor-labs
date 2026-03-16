"use client";

import { useState, useEffect, useCallback } from "react";
import { useSession } from "next-auth/react";
import type { ScreenerFilter, SavedScreener } from "@/types";
import { useSavedScreeners } from "@/hooks/useSavedScreeners";
import { Button } from "@/components/ui/button";
import { PremiumGate } from "@/components/common/PremiumGate";

interface SavedScreenerPanelProps {
  filters: ScreenerFilter;
  onLoadScreener: (filters: ScreenerFilter) => void;
  activeFilterCount: number;
}

export function SavedScreenerPanel({
  filters,
  onLoadScreener,
  activeFilterCount,
}: SavedScreenerPanelProps) {
  const { data: session, status: authStatus } = useSession();
  const isAuthenticated = authStatus === "authenticated" && !!session?.user;
  const isPremium = session?.user?.premiumStatus === "premium";

  // Only fetch saved screeners for premium users
  const {
    savedScreeners,
    isLoading,
    saveScreener,
    updateScreener,
    deleteScreener,
    isSaving,
  } = useSavedScreeners(isPremium);

  const [isSaveMode, setIsSaveMode] = useState(false);
  const [saveName, setSaveName] = useState("");
  const [showSavedFeedback, setShowSavedFeedback] = useState(false);
  const [loadedScreenerId, setLoadedScreenerId] = useState<number | null>(null);

  // Clear feedback after 2 seconds
  useEffect(() => {
    if (!showSavedFeedback) return;
    const timer = setTimeout(() => setShowSavedFeedback(false), 2000);
    return () => clearTimeout(timer);
  }, [showSavedFeedback]);

  const handleSave = useCallback(async () => {
    if (!saveName.trim()) return;
    try {
      await saveScreener({ name: saveName.trim(), filters_json: filters });
      setSaveName("");
      setIsSaveMode(false);
      setShowSavedFeedback(true);
    } catch {
      // Error is surfaced by TanStack Query
    }
  }, [saveName, filters, saveScreener]);

  const handleLoad = useCallback(
    (screener: SavedScreener) => {
      setLoadedScreenerId(screener.id);
      onLoadScreener(screener.filters_json);
    },
    [onLoadScreener],
  );

  const handleUpdate = useCallback(
    async (screener: SavedScreener) => {
      try {
        await updateScreener({ id: screener.id, filters_json: filters });
      } catch {
        // Error is surfaced by TanStack Query
      }
    },
    [filters, updateScreener],
  );

  const handleDelete = useCallback(
    async (id: number) => {
      try {
        await deleteScreener(id);
        if (loadedScreenerId === id) {
          setLoadedScreenerId(null);
        }
      } catch {
        // Error is surfaced by TanStack Query
      }
    },
    [deleteScreener, loadedScreenerId],
  );

  // Unauthenticated: show sign-in prompt
  if (!isAuthenticated) {
    return (
      <div className="mt-4 border-t border-zinc-800 pt-4">
        <p className="text-xs text-zinc-500">
          Sign in to save your screener configurations.
        </p>
      </div>
    );
  }

  // Authenticated but not premium: show PremiumGate
  if (!isPremium) {
    return (
      <div className="mt-4 border-t border-zinc-800 pt-4">
        <PremiumGate featureName="Saved Screeners">
          <div className="space-y-2">
            <Button variant="outline" size="sm" className="w-full" disabled>
              Save Screener
            </Button>
            <p className="text-xs text-zinc-500">
              No saved screeners yet.
            </p>
          </div>
        </PremiumGate>
      </div>
    );
  }

  // Premium user: full functionality
  return (
    <div className="mt-4 border-t border-zinc-800 pt-4">
      {/* Save button / feedback */}
      {showSavedFeedback ? (
        <p className="text-center text-sm font-medium text-green-400">
          Saved
        </p>
      ) : isSaveMode ? (
        <div className="space-y-2">
          <input
            type="text"
            value={saveName}
            onChange={(e) => setSaveName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleSave();
              if (e.key === "Escape") setIsSaveMode(false);
            }}
            placeholder="Screener name..."
            maxLength={100}
            className="w-full rounded-md border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-200 focus:outline-none focus:ring-2 focus:ring-violet-500"
            aria-label="Screener name"
          />
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              className="flex-1"
              onClick={handleSave}
              disabled={!saveName.trim() || isSaving}
            >
              {isSaving ? "Saving..." : "Confirm"}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setIsSaveMode(false);
                setSaveName("");
              }}
            >
              Cancel
            </Button>
          </div>
        </div>
      ) : (
        <Button
          variant="outline"
          size="sm"
          className="w-full border-violet-600 text-violet-400 hover:bg-violet-600/10"
          onClick={() => setIsSaveMode(true)}
          disabled={activeFilterCount === 0}
        >
          Save Screener
        </Button>
      )}

      {/* Saved screeners list */}
      <div className="mt-3">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
          Saved Screeners
        </h3>

        {isLoading ? (
          <p className="mt-2 text-xs text-zinc-500">Loading...</p>
        ) : savedScreeners.length === 0 ? (
          <p className="mt-2 text-xs text-zinc-500">
            No saved screeners yet. Apply filters and save your first
            configuration.
          </p>
        ) : (
          <ul className="mt-2 space-y-1">
            {savedScreeners.map((screener) => (
              <li
                key={screener.id}
                className="group flex items-center justify-between rounded px-2 py-1.5 hover:bg-zinc-800"
              >
                <button
                  className="flex-1 text-left text-sm text-zinc-300 hover:text-white"
                  onClick={() => handleLoad(screener)}
                  title={`Load "${screener.name}"`}
                >
                  {screener.name}
                </button>
                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100">
                  {loadedScreenerId === screener.id && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 px-1.5 text-xs text-violet-400"
                      onClick={() => handleUpdate(screener)}
                      title="Update with current filters"
                    >
                      Update
                    </Button>
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 w-6 p-0 text-zinc-500 hover:text-red-400"
                    onClick={() => handleDelete(screener.id)}
                    title={`Delete "${screener.name}"`}
                    aria-label={`Delete ${screener.name}`}
                  >
                    &times;
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
