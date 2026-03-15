"use client";

import { useState } from "react";
import { Search } from "lucide-react";
import { Button } from "@/components/ui/button";

const SS58_REGEX = /^[1-9A-HJ-NP-Za-km-z]{46,48}$/;

interface ExploreAddressInputProps {
  onSubmit: (address: string) => void;
  isLoading: boolean;
}

export function ExploreAddressInput({
  onSubmit,
  isLoading,
}: ExploreAddressInputProps) {
  const [input, setInput] = useState("");
  const [error, setError] = useState<string | null>(null);

  function handleSubmit() {
    const trimmed = input.trim();
    if (!SS58_REGEX.test(trimmed)) {
      setError("Invalid coldkey address. Please enter a valid SS58 address.");
      return;
    }
    setError(null);
    onSubmit(trimmed);
    setInput("");
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSubmit();
    }
  }

  return (
    <div className="space-y-2">
      <div className="flex gap-3">
        <input
          type="text"
          value={input}
          onChange={(e) => {
            setInput(e.target.value);
            if (error) setError(null);
          }}
          onKeyDown={handleKeyDown}
          placeholder="Paste a coldkey address (e.g., 5F3sa2...)"
          aria-label="Coldkey address"
          className="min-h-[44px] flex-1 rounded-md border border-border bg-surface px-3 py-2 font-mono text-sm text-text-primary placeholder:text-text-muted focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
        />
        <Button
          onClick={handleSubmit}
          disabled={isLoading || input.trim().length === 0}
          className="min-h-[44px] min-w-[44px]"
        >
          <Search />
          View Portfolio
        </Button>
      </div>
      {error && (
        <p className="text-sm text-rose-500" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
