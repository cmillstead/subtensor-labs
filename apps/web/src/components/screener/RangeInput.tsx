"use client";

import { useEffect, useRef, useState } from "react";

interface RangeInputProps {
  label: string;
  minValue: number | null;
  maxValue: number | null;
  onMinChange: (val: number | null) => void;
  onMaxChange: (val: number | null) => void;
  step?: number;
  suffix?: string;
  placeholderMin?: string;
  placeholderMax?: string;
}

export function RangeInput({
  label,
  minValue,
  maxValue,
  onMinChange,
  onMaxChange,
  step = 1,
  suffix,
  placeholderMin = "Min",
  placeholderMax = "Max",
}: RangeInputProps) {
  const [localMin, setLocalMin] = useState<string>(
    minValue !== null ? String(minValue) : "",
  );
  const [localMax, setLocalMax] = useState<string>(
    maxValue !== null ? String(maxValue) : "",
  );
  const minTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const maxTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Sync external changes into local state
  useEffect(() => {
    setLocalMin(minValue !== null ? String(minValue) : "");
  }, [minValue]);

  useEffect(() => {
    setLocalMax(maxValue !== null ? String(maxValue) : "");
  }, [maxValue]);

  const hasError =
    localMin !== "" &&
    localMax !== "" &&
    Number(localMin) > Number(localMax);

  function handleMinChange(value: string) {
    setLocalMin(value);
    if (minTimerRef.current) clearTimeout(minTimerRef.current);
    minTimerRef.current = setTimeout(() => {
      onMinChange(value === "" ? null : Number(value));
    }, 300);
  }

  function handleMaxChange(value: string) {
    setLocalMax(value);
    if (maxTimerRef.current) clearTimeout(maxTimerRef.current);
    maxTimerRef.current = setTimeout(() => {
      onMaxChange(value === "" ? null : Number(value));
    }, 300);
  }

  // Cleanup timers on unmount
  useEffect(() => {
    return () => {
      if (minTimerRef.current) clearTimeout(minTimerRef.current);
      if (maxTimerRef.current) clearTimeout(maxTimerRef.current);
    };
  }, []);

  const inputClasses = `min-h-[44px] w-full rounded-md border bg-zinc-900 px-3 py-2 text-sm text-text-primary placeholder:text-text-secondary/50 focus:outline-none focus:ring-2 focus:ring-violet-500 ${
    hasError ? "border-rose-500" : "border-zinc-700"
  }`;

  const filterId = label.toLowerCase().replace(/\s+/g, "-");

  return (
    <fieldset className="space-y-1.5">
      <legend className="text-xs font-medium text-text-secondary">
        {label}
        {suffix && (
          <span className="ml-1 text-text-secondary/60">({suffix})</span>
        )}
      </legend>
      <div className="flex items-center gap-2">
        <div className="flex-1">
          <label htmlFor={`${filterId}-min`} className="sr-only">
            {label} minimum
          </label>
          <input
            id={`${filterId}-min`}
            type="number"
            className={inputClasses}
            value={localMin}
            onChange={(e) => handleMinChange(e.target.value)}
            placeholder={placeholderMin}
            step={step}
            aria-label={`${label} minimum`}
          />
        </div>
        <span className="text-xs text-text-secondary/60" aria-hidden="true">
          –
        </span>
        <div className="flex-1">
          <label htmlFor={`${filterId}-max`} className="sr-only">
            {label} maximum
          </label>
          <input
            id={`${filterId}-max`}
            type="number"
            className={inputClasses}
            value={localMax}
            onChange={(e) => handleMaxChange(e.target.value)}
            placeholder={placeholderMax}
            step={step}
            aria-label={`${label} maximum`}
          />
        </div>
      </div>
      {hasError && (
        <p className="text-xs text-rose-400" role="alert">
          Min cannot exceed max
        </p>
      )}
    </fieldset>
  );
}
