"use client";

import { useState, useCallback } from "react";
import { cn } from "@/lib/utils";
import { X } from "lucide-react";

const MAX_ADDRESSES = 20;
// Base58 charset (no 0, O, I, l) — matches backend validation
const SS58_PATTERN = /^[1-9A-HJ-NP-Za-km-z]{46,48}$/;

interface AddressManagerProps {
  addresses: string[];
  onAddressesChange: (addresses: string[]) => void;
  className?: string;
}

export function AddressManager({
  addresses,
  onAddressesChange,
  className,
}: AddressManagerProps) {
  const [inputValue, setInputValue] = useState("");
  const [error, setError] = useState<string | null>(null);

  const handleAdd = useCallback(() => {
    const trimmed = inputValue.trim();

    if (!trimmed) {
      setError("Please enter a coldkey address");
      return;
    }

    if (!SS58_PATTERN.test(trimmed)) {
      setError("Invalid SS58 address format (46-48 base58 characters)");
      return;
    }

    if (addresses.includes(trimmed)) {
      setError("Address already added");
      return;
    }

    if (addresses.length >= MAX_ADDRESSES) {
      setError(`Maximum ${MAX_ADDRESSES} addresses allowed`);
      return;
    }

    onAddressesChange([...addresses, trimmed]);
    setInputValue("");
    setError(null);
  }, [inputValue, addresses, onAddressesChange]);

  const handleRemove = useCallback(
    (address: string) => {
      onAddressesChange(addresses.filter((a) => a !== address));
    },
    [addresses, onAddressesChange],
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter") {
        e.preventDefault();
        handleAdd();
      }
    },
    [handleAdd],
  );

  return (
    <div className={cn("space-y-3", className)}>
      <div className="flex gap-2">
        <input
          type="text"
          value={inputValue}
          onChange={(e) => {
            setInputValue(e.target.value);
            setError(null);
          }}
          onKeyDown={handleKeyDown}
          placeholder="Paste coldkey address (e.g., 5D...)"
          aria-label="Coldkey address input"
          aria-invalid={error ? "true" : undefined}
          aria-describedby={error ? "address-error" : undefined}
          className={cn(
            "flex-1 rounded-md border bg-surface px-3 py-2 text-sm text-text-primary",
            "placeholder:text-text-muted",
            "focus:outline-none focus:ring-2 focus:ring-primary",
            error ? "border-error" : "border-border",
          )}
        />
        <button
          onClick={handleAdd}
          disabled={addresses.length >= MAX_ADDRESSES}
          className={cn(
            "rounded-md bg-primary px-4 py-2 text-sm font-medium text-white",
            "hover:bg-primary-hover transition-colors",
            "disabled:opacity-50 disabled:cursor-not-allowed",
            "min-h-[44px] min-w-[44px]",
          )}
        >
          Add Address
        </button>
      </div>

      {error && (
        <p id="address-error" className="text-xs text-error" role="alert">
          {error}
        </p>
      )}

      {addresses.length > 0 && (
        <ul className="space-y-1" aria-label="Added addresses">
          {addresses.map((address) => (
            <li
              key={address}
              className="flex items-center justify-between rounded-md border border-border bg-surface px-3 py-2"
            >
              <span className="font-mono text-xs text-text-secondary truncate mr-2">
                {address}
              </span>
              <button
                onClick={() => handleRemove(address)}
                aria-label={`Remove address ${address.slice(0, 6)}...${address.slice(-6)}`}
                className={cn(
                  "flex-shrink-0 rounded p-1 text-text-muted",
                  "hover:text-error hover:bg-elevated transition-colors",
                  "min-h-[44px] min-w-[44px] flex items-center justify-center",
                )}
              >
                <X size={14} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
