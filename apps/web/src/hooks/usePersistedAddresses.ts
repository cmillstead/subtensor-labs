"use client";

import { useState, useEffect, useCallback } from "react";
import type { LabeledAddress } from "@/types";

const STORAGE_KEY = "subtensor-labs:addresses";

function readFromStorage(): LabeledAddress[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    // Validate shape: each item must have address string
    return parsed.filter(
      (item: unknown): item is LabeledAddress =>
        typeof item === "object" &&
        item !== null &&
        typeof (item as LabeledAddress).address === "string" &&
        typeof (item as LabeledAddress).label === "string",
    );
  } catch {
    return [];
  }
}

function writeToStorage(addresses: LabeledAddress[]): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(addresses));
  } catch {
    // Storage quota exceeded or unavailable — silently ignore
  }
}

export function usePersistedAddresses() {
  const [addresses, setAddressesState] = useState<LabeledAddress[]>([]);
  const [hydrated, setHydrated] = useState(false);

  // Read from localStorage on mount (client-side only)
  useEffect(() => {
    setAddressesState(readFromStorage());
    setHydrated(true);
  }, []);

  const setAddresses = useCallback(
    (next: LabeledAddress[]) => {
      setAddressesState(next);
      writeToStorage(next);
    },
    [],
  );

  return { addresses, setAddresses, hydrated } as const;
}
