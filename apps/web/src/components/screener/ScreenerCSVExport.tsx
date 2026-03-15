"use client";

import { Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  generateScreenerCsv,
  generateScreenerFilename,
  downloadCsv,
} from "@/lib/csv";
import type { ScreenerSubnet } from "@/types";

interface ScreenerCSVExportProps {
  subnets: ScreenerSubnet[] | undefined;
  isLoading: boolean;
}

export function ScreenerCSVExport({
  subnets,
  isLoading,
}: ScreenerCSVExportProps) {
  const disabled = isLoading || !subnets || subnets.length === 0;

  const title = isLoading
    ? "Loading screener data…"
    : !subnets || subnets.length === 0
      ? "No subnet data to export"
      : "Export screener results as CSV";

  function handleClick() {
    if (!subnets) return;
    const csv = generateScreenerCsv(subnets);
    const filename = generateScreenerFilename();
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
