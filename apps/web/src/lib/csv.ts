import type { PortfolioResult, ScreenerSubnet } from "@/types";

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

/* ── Screener CSV ────────────────────────────────────────────────── */

const SCREENER_HEADERS = [
  "netuid",
  "name",
  "miner_count",
  "validator_count",
  "registration_cost",
  "emission_share_pct",
  "alpha_price",
  "alpha_market_cap",
  "fill_rate_pct",
  "owner_take_rate_pct",
  "tao_reserves",
  "alpha_reserves",
  "subnet_age_days",
] as const;

export function generateScreenerCsv(subnets: ScreenerSubnet[]): string {
  const lines: string[] = [SCREENER_HEADERS.join(",")];

  for (const s of subnets) {
    const fields = [
      formatValue(s.netuid),
      formatValue(s.name),
      formatValue(s.miner_count),
      formatValue(s.validator_count),
      formatValue(s.registration_cost),
      formatValue(s.emission_share * 100),
      formatValue(s.alpha_price),
      formatValue(s.alpha_market_cap),
      formatValue(s.fill_rate * 100),
      formatValue(s.owner_take_rate * 100),
      formatValue(s.tao_reserves),
      formatValue(s.alpha_reserves),
      formatValue(s.subnet_age_days),
    ];
    lines.push(fields.map(escapeField).join(","));
  }

  return lines.join("\n");
}

export function generateScreenerFilename(): string {
  const date = new Date().toISOString().slice(0, 10);
  return `subtensor-labs-screener-${date}.csv`;
}

/* ── Shared download helper ──────────────────────────────────────── */

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
