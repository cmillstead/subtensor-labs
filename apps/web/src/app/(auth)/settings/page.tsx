"use client";

import { QueryClientProvider } from "@tanstack/react-query";
import { getQueryClient } from "@/lib/query-client";
import { AddressManager } from "@/components/portfolio/AddressManager";
import { useAddresses } from "@/hooks/useAddresses";
import { Loader2 } from "lucide-react";

function SettingsContent() {
  const {
    addresses, setAddresses, addAddress, removeAddress, updateLabel,
    isLoading, hydrated,
  } = useAddresses();

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-text-primary">Settings</h1>
        <p className="mt-1 text-sm text-text-secondary">
          Manage your saved addresses and account preferences.
        </p>
      </header>

      <section className="rounded-lg border border-border bg-surface p-6">
        <h2 className="mb-4 text-lg font-semibold text-text-primary">
          Saved Addresses
        </h2>

        {isLoading && !hydrated ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-text-muted" />
          </div>
        ) : (
          <AddressManager
            addresses={addresses}
            onAddressesChange={setAddresses}
            onAdd={addAddress}
            onRemove={removeAddress}
            onUpdateLabel={updateLabel}
          />
        )}
      </section>
    </div>
  );
}

export default function SettingsPage() {
  const queryClient = getQueryClient();

  return (
    <QueryClientProvider client={queryClient}>
      <SettingsContent />
    </QueryClientProvider>
  );
}
