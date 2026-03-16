"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type { SavedScreener, ScreenerFilter } from "@/types";

const SAVED_SCREENERS_KEY = ["saved-screeners"];

async function fetchSavedScreeners(): Promise<SavedScreener[]> {
  const res = await fetch("/api/screener/saved");
  if (!res.ok) {
    throw new Error("Failed to fetch saved screeners");
  }
  const json = await res.json();
  return json.data;
}

export function useSavedScreeners(enabled = true) {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: SAVED_SCREENERS_KEY,
    queryFn: fetchSavedScreeners,
    enabled,
  });

  const createMutation = useMutation({
    mutationFn: async (params: { name: string; filters_json: ScreenerFilter }) => {
      const res = await fetch("/api/screener/saved", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(params),
      });
      if (!res.ok) {
        const json = await res.json();
        throw new Error(json.error?.message || "Failed to save screener");
      }
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: SAVED_SCREENERS_KEY });
    },
  });

  const updateMutation = useMutation({
    mutationFn: async (params: {
      id: number;
      name?: string;
      filters_json?: ScreenerFilter;
    }) => {
      const { id, ...body } = params;
      const res = await fetch(`/api/screener/saved/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const json = await res.json();
        throw new Error(json.error?.message || "Failed to update screener");
      }
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: SAVED_SCREENERS_KEY });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      const res = await fetch(`/api/screener/saved/${id}`, { method: "DELETE" });
      if (!res.ok) {
        const json = await res.json();
        throw new Error(json.error?.message || "Failed to delete screener");
      }
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: SAVED_SCREENERS_KEY });
    },
  });

  return {
    savedScreeners: query.data ?? [],
    isLoading: query.isLoading,
    saveScreener: createMutation.mutateAsync,
    updateScreener: updateMutation.mutateAsync,
    deleteScreener: deleteMutation.mutateAsync,
    isSaving: createMutation.isPending,
    isDeleting: deleteMutation.isPending,
  };
}
