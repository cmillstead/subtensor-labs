import { TaoAmount } from "@/components/common/TaoAmount";
import type { SubnetDetail } from "@/types";

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(2)}%`;
}

interface MetricCardProps {
  label: string;
  children: React.ReactNode;
}

function MetricCard({ label, children }: MetricCardProps) {
  return (
    <div className="rounded-lg border border-border bg-surface p-4">
      <p className="text-xs text-text-muted">{label}</p>
      <div className="mt-1 text-lg font-semibold text-text-primary">
        {children}
      </div>
    </div>
  );
}

interface SubnetMetricsProps {
  detail: SubnetDetail;
}

export function SubnetMetrics({ detail }: SubnetMetricsProps) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
      <MetricCard label="Miner Count">
        <span className="font-mono">{detail.miner_count.toLocaleString()}</span>
      </MetricCard>
      <MetricCard label="Validator Count">
        <span className="font-mono">{detail.validator_count.toLocaleString()}</span>
      </MetricCard>
      <MetricCard label="Registration Cost">
        <TaoAmount value={detail.registration_cost} size="small" />
      </MetricCard>
      <MetricCard label="Emission Share">
        <span className="font-mono">{formatPercent(detail.emission_share)}</span>
      </MetricCard>
      <MetricCard label="Alpha Price">
        <TaoAmount value={detail.alpha_price} size="small" />
      </MetricCard>
      <MetricCard label="Market Cap">
        <TaoAmount value={detail.alpha_market_cap} size="small" abbreviate />
      </MetricCard>
      <MetricCard label="TAO Reserves">
        <TaoAmount value={detail.tao_reserves} size="small" abbreviate />
      </MetricCard>
      <MetricCard label="Fill Rate">
        <span className="font-mono">{formatPercent(detail.fill_rate)}</span>
      </MetricCard>
      <MetricCard label="Owner Take Rate">
        <span className="font-mono">{formatPercent(detail.owner_take_rate)}</span>
      </MetricCard>
      <MetricCard label="Subnet Age">
        <span className="font-mono">
          {detail.subnet_age_days.toLocaleString()} {detail.subnet_age_days === 1 ? "day" : "days"}
        </span>
      </MetricCard>
    </div>
  );
}
