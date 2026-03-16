"use client";

import { useSession } from "next-auth/react";
import { useEffect, useRef, useCallback } from "react";
import { usePersistedAddresses } from "./usePersistedAddresses";
import { useServerAddresses } from "./useServerAddresses";
import type { LabeledAddress } from "@/types";

const STORAGE_KEY = "subtensor-labs:addresses";

/**
 * Unified address hook — server-backed when authenticated, localStorage when anonymous.
 * On first authenticated load with local addresses, merges them to the server and clears localStorage.
 */
export function useAddresses() {
  const { data: session, status: authStatus } = useSession();
  const isAuthenticated = authStatus === "authenticated" && !!session?.user;
  const isAuthLoading = authStatus === "loading";

  const local = usePersistedAddresses();
  const server = useServerAddresses();
  const mergeAttempted = useRef(false);
  const serverAddAddressRef = useRef(server.addAddress);
  serverAddAddressRef.current = server.addAddress;

  // Merge localStorage addresses to server on first authenticated load
  useEffect(() => {
    if (!isAuthenticated || mergeAttempted.current || server.isLoading) return;
    mergeAttempted.current = true;

    const localAddresses = local.addresses;
    if (localAddresses.length === 0) return;

    const serverAddressSet = new Set(
      server.addresses.map((a) => a.coldkey_address),
    );

    const toSync = localAddresses.filter(
      (la) => !serverAddressSet.has(la.address),
    );

    if (toSync.length === 0) {
      // All local addresses already exist on server — just clear localStorage
      if (typeof window !== "undefined") {
        localStorage.removeItem(STORAGE_KEY);
      }
      return;
    }

    // Sync each local address to server, then clear localStorage
    const addFn = serverAddAddressRef.current;
    Promise.all(
      toSync.map((la) =>
        addFn({
          coldkey_address: la.address,
          label: la.label || undefined,
        }).catch(() => {
          // Individual failures are non-fatal — address may already exist
        }),
      ),
    ).then(() => {
      if (typeof window !== "undefined") {
        localStorage.removeItem(STORAGE_KEY);
      }
    });
  }, [isAuthenticated, server.isLoading, server.addresses, local.addresses]);

  // Convert server addresses to LabeledAddress format
  const serverAsLabeled: LabeledAddress[] = server.addresses.map((a) => ({
    address: a.coldkey_address,
    label: a.label ?? "",
  }));

  const addAddress = useCallback(
    async (address: string, label: string) => {
      if (isAuthenticated) {
        await server.addAddress({
          coldkey_address: address,
          label: label || undefined,
        });
      } else {
        local.setAddresses([...local.addresses, { address, label }]);
      }
    },
    [isAuthenticated, server, local],
  );

  const removeAddress = useCallback(
    async (address: string) => {
      if (isAuthenticated) {
        const serverAddr = server.addresses.find(
          (a) => a.coldkey_address === address,
        );
        if (serverAddr) {
          await server.removeAddress(serverAddr.id);
        }
      } else {
        local.setAddresses(local.addresses.filter((a) => a.address !== address));
      }
    },
    [isAuthenticated, server, local],
  );

  const updateLabel = useCallback(
    async (address: string, newLabel: string) => {
      if (isAuthenticated) {
        const serverAddr = server.addresses.find(
          (a) => a.coldkey_address === address,
        );
        if (serverAddr) {
          await server.updateLabel({ id: serverAddr.id, label: newLabel || null });
        }
      } else {
        local.setAddresses(
          local.addresses.map((a) =>
            a.address === address ? { ...a, label: newLabel } : a,
          ),
        );
      }
    },
    [isAuthenticated, server, local],
  );

  // setAddresses for backward compatibility (used by AddressManager's onAddressesChange)
  const setAddresses = useCallback(
    (next: LabeledAddress[]) => {
      if (!isAuthenticated) {
        local.setAddresses(next);
      }
      // For authenticated users, individual operations (add/remove/updateLabel) are used instead
    },
    [isAuthenticated, local],
  );

  return {
    addresses: isAuthenticated ? serverAsLabeled : local.addresses,
    setAddresses,
    addAddress,
    removeAddress,
    updateLabel,
    hydrated: isAuthenticated ? !server.isLoading : local.hydrated,
    isAuthenticated,
    isLoading: isAuthLoading || (isAuthenticated && server.isLoading),
    serverAddresses: isAuthenticated ? server.addresses : [],
  } as const;
}
