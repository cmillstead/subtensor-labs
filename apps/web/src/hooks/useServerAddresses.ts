"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type { ServerAddress } from "@/types";

const ADDRESSES_KEY = ["addresses"];

async function fetchAddresses(): Promise<ServerAddress[]> {
  const res = await fetch("/api/addresses");
  if (!res.ok) {
    throw new Error("Failed to fetch addresses");
  }
  const json = await res.json();
  return json.data;
}

export function useServerAddresses() {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ADDRESSES_KEY,
    queryFn: fetchAddresses,
  });

  const addMutation = useMutation({
    mutationFn: async (params: { coldkey_address: string; label?: string }) => {
      const res = await fetch("/api/addresses", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(params),
      });
      if (!res.ok) {
        const json = await res.json();
        throw new Error(json.error?.message || "Failed to add address");
      }
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ADDRESSES_KEY });
    },
  });

  const updateLabelMutation = useMutation({
    mutationFn: async (params: { id: number; label: string | null }) => {
      const res = await fetch(`/api/addresses/${params.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ label: params.label }),
      });
      if (!res.ok) {
        const json = await res.json();
        throw new Error(json.error?.message || "Failed to update label");
      }
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ADDRESSES_KEY });
    },
  });

  const removeMutation = useMutation({
    mutationFn: async (id: number) => {
      const res = await fetch(`/api/addresses/${id}`, { method: "DELETE" });
      if (!res.ok) {
        const json = await res.json();
        throw new Error(json.error?.message || "Failed to remove address");
      }
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ADDRESSES_KEY });
    },
  });

  return {
    addresses: query.data ?? [],
    isLoading: query.isLoading,
    addAddress: addMutation.mutateAsync,
    updateLabel: updateLabelMutation.mutateAsync,
    removeAddress: removeMutation.mutateAsync,
    isAdding: addMutation.isPending,
    isRemoving: removeMutation.isPending,
  };
}
