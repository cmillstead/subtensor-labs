"use client";

import { Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  generatePortfolioCsv,
  generatePortfolioFilename,
  downloadCsv,
} from "@/lib/csv";
import type { PortfolioResult } from "@/types";

interface ExportCsvButtonProps {
  data: PortfolioResult | undefined;
  isLoading: boolean;
}

export function ExportCsvButton({ data, isLoading }: ExportCsvButtonProps) {
  const disabled = isLoading || !data || data.positions.length === 0;

  const title = isLoading
    ? "Loading portfolio data…"
    : !data || data.positions.length === 0
      ? "No portfolio data to export"
      : "Export portfolio as CSV";

  function handleClick() {
    if (!data) return;
    const csv = generatePortfolioCsv(data);
    const filename = generatePortfolioFilename();
    downloadCsv(csv, filename);
  }

  return (
    <Button
      variant="outline"
      size="sm"
      onClick={handleClick}
      disabled={disabled}
      title={title}
      className="min-h-[44px] min-w-[44px]"
    >
      <Download />
      Export CSV
    </Button>
  );
}
