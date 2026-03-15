"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { cn } from "@/lib/utils";
import { X, Pencil, Check } from "lucide-react";
import type { LabeledAddress } from "@/types";

const MAX_ADDRESSES = 20;
// Base58 charset (no 0, O, I, l) — matches backend validation
const SS58_PATTERN = /^[1-9A-HJ-NP-Za-km-z]{46,48}$/;

function truncateAddress(address: string): string {
  if (address.length <= 12) return address;
  return `${address.slice(0, 6)}...${address.slice(-6)}`;
}

interface AddressManagerProps {
  addresses: LabeledAddress[];
  onAddressesChange: (addresses: LabeledAddress[]) => void;
  className?: string;
}

export function AddressManager({
  addresses,
  onAddressesChange,
  className,
}: AddressManagerProps) {
  const [inputValue, setInputValue] = useState("");
  const [labelValue, setLabelValue] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editLabelValue, setEditLabelValue] = useState("");

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

    if (addresses.some((a) => a.address === trimmed)) {
      setError("Address already added");
      return;
    }

    if (addresses.length >= MAX_ADDRESSES) {
      setError(`Maximum ${MAX_ADDRESSES} addresses allowed`);
      return;
    }

    onAddressesChange([
      ...addresses,
      { address: trimmed, label: labelValue.trim() },
    ]);
    setInputValue("");
    setLabelValue("");
    setError(null);
  }, [inputValue, labelValue, addresses, onAddressesChange]);

  const handleRemove = useCallback(
    (address: string) => {
      onAddressesChange(addresses.filter((a) => a.address !== address));
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

  const startEdit = useCallback(
    (index: number) => {
      setEditingIndex(index);
      setEditLabelValue(addresses[index].label);
    },
    [addresses],
  );

  const saveEdit = useCallback(() => {
    if (editingIndex === null) return;
    const updated = addresses.map((a, i) =>
      i === editingIndex ? { ...a, label: editLabelValue.trim() } : a,
    );
    onAddressesChange(updated);
    setEditingIndex(null);
    setEditLabelValue("");
  }, [editingIndex, editLabelValue, addresses, onAddressesChange]);

  const editInputRef = useRef<HTMLInputElement>(null);

  // Focus edit input when entering edit mode
  useEffect(() => {
    if (editingIndex !== null) {
      editInputRef.current?.focus();
    }
  }, [editingIndex]);

  const cancelEdit = useCallback(() => {
    setEditingIndex(null);
    setEditLabelValue("");
  }, []);

  const handleEditKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter") {
        e.preventDefault();
        saveEdit();
      } else if (e.key === "Escape") {
        cancelEdit();
      }
    },
    [saveEdit, cancelEdit],
  );

  return (
    <div className={cn("space-y-3", className)}>
      <div className="flex flex-col gap-2 sm:flex-row">
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
        <input
          type="text"
          value={labelValue}
          onChange={(e) => setLabelValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Label (optional)"
          aria-label="Address label"
          className={cn(
            "rounded-md border border-border bg-surface px-3 py-2 text-sm text-text-primary",
            "placeholder:text-text-muted",
            "focus:outline-none focus:ring-2 focus:ring-primary",
            "sm:w-40",
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
          {addresses.map((entry, index) => (
            <li
              key={entry.address}
              className="flex items-center justify-between rounded-md border border-border bg-surface px-3 py-2"
            >
              <div className="flex items-center gap-2 min-w-0 mr-2">
                {editingIndex === index ? (
                  <div className="flex items-center gap-1">
                    <input
                      type="text"
                      value={editLabelValue}
                      onChange={(e) => setEditLabelValue(e.target.value)}
                      onKeyDown={handleEditKeyDown}
                      ref={editInputRef}
                      aria-label="Edit address label"
                      className={cn(
                        "rounded border border-border bg-elevated px-2 py-1 text-xs text-text-primary",
                        "focus:outline-none focus:ring-1 focus:ring-primary",
                        "w-32",
                      )}
                    />
                    <button
                      onClick={saveEdit}
                      aria-label="Save label"
                      className={cn(
                        "rounded p-1 text-text-muted",
                        "hover:text-accent hover:bg-elevated transition-colors",
                        "min-h-[44px] min-w-[44px] flex items-center justify-center",
                      )}
                    >
                      <Check size={14} />
                    </button>
                  </div>
                ) : (
                  <>
                    {entry.label ? (
                      <span className="text-xs font-medium text-text-primary truncate">
                        {entry.label}
                      </span>
                    ) : null}
                    <span className="font-mono text-xs text-text-secondary truncate">
                      {entry.label
                        ? truncateAddress(entry.address)
                        : entry.address}
                    </span>
                    <button
                      onClick={() => startEdit(index)}
                      aria-label={`Edit label for ${truncateAddress(entry.address)}`}
                      className={cn(
                        "flex-shrink-0 rounded p-1 text-text-muted",
                        "hover:text-accent hover:bg-elevated transition-colors",
                        "min-h-[44px] min-w-[44px] flex items-center justify-center",
                      )}
                    >
                      <Pencil size={12} />
                    </button>
                  </>
                )}
              </div>
              <button
                onClick={() => handleRemove(entry.address)}
                aria-label={`Remove address ${truncateAddress(entry.address)}`}
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
