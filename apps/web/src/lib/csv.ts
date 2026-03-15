import type { PortfolioResult } from "@/types";

const CSV_HEADERS = [
  "subnet_name",
  "netuid",
  "staked_tao",
  "alpha_holdings",
  "alpha_value_tao",
  "emission_share_pct",
  "is_miner",
  "incentive",
  "trust",
  "dividends",
  "validator_name",
  "delegation_amount_tao",
  "delegation_apy_pct",
  "delegation_take_rate_pct",
] as const;

function escapeField(value: string): string {
  if (value.includes(",") || value.includes('"') || value.includes("\n")) {
    return `"${value.replace(/"/g, '""')}"`;
  }
  return value;
}

function formatNumber(value: number): string {
  return parseFloat(value.toPrecision(15)).toString();
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "number") return formatNumber(value);
  return String(value);
}

export function generatePortfolioCsv(result: PortfolioResult): string {
  const lines: string[] = [CSV_HEADERS.join(",")];

  for (const pos of result.positions) {
    const positionFields = [
      formatValue(pos.subnet_name),
      formatValue(pos.netuid),
      formatValue(pos.staked_tao),
      formatValue(pos.alpha_holdings),
      formatValue(pos.alpha_value_tao),
      formatValue(pos.emission_share * 100),
      formatValue(pos.is_miner),
      formatValue(pos.incentive),
      formatValue(pos.trust),
      formatValue(pos.dividends),
      "", // validator_name
      "", // delegation_amount_tao
      "", // delegation_apy_pct
      "", // delegation_take_rate_pct
    ];
    lines.push(positionFields.map(escapeField).join(","));

    for (const del of pos.delegations) {
      const delegationFields = [
        formatValue(pos.subnet_name),
        formatValue(pos.netuid),
        "", // staked_tao
        "", // alpha_tokens
        "", // alpha_value_tao
        "", // emission_share_pct
        "", // is_miner
        "", // incentive
        "", // trust
        "", // dividends
        formatValue(del.validator_name),
        formatValue(del.delegated_amount),
        formatValue(del.estimated_apy),
        formatValue(del.take_rate * 100),
      ];
      lines.push(delegationFields.map(escapeField).join(","));
    }
  }

  return lines.join("\n");
}

export function generatePortfolioFilename(): string {
  const date = new Date().toISOString().slice(0, 10);
  return `subtensor-labs-portfolio-${date}.csv`;
}

export function downloadCsv(csvContent: string, filename: string): void {
  const bom = "\uFEFF";
  const blob = new Blob([bom + csvContent], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
