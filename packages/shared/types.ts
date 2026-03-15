/**
 * Shared TypeScript type definitions used across Subtensor Labs.
 * Python engine uses equivalent Pydantic schemas (manually kept in sync).
 */

/** Subnet snapshot data from TimescaleDB */
export interface SubnetSnapshot {
  time: string;
  netuid: number;
  miner_count: number;
  validator_count: number;
  emission_share: number;
  registration_cost: number;
  alpha_price: number;
  alpha_market_cap: number;
  tao_reserves: number;
  alpha_reserves: number;
  fill_rate: number;
  owner_take_rate: number;
}

/** Alpha token price record */
export interface AlphaPrice {
  time: string;
  netuid: number;
  price_tao: number;
  tao_reserve: number;
  alpha_reserve: number;
  volume_24h: number | null;
}

/** Portfolio position for a single subnet */
export interface SubnetPosition {
  netuid: number;
  subnet_name: string | null;
  hotkey: string;
  staked_tao: number;
  alpha_holdings: number;
  alpha_value_tao: number;
  emission_share: number;
  incentive: number;
  trust: number;
  dividends: number;
  is_active: boolean;
  is_miner: boolean;
  delegations: DelegationDetail[];
}

/** Delegation detail for a validator */
export interface DelegationDetail {
  validator_hotkey: string;
  validator_name: string | null;
  delegated_amount: number;
  estimated_apy: number | null;
  take_rate: number;
}

/** Complete portfolio aggregation result (matches Python PortfolioResponseSchema) */
export interface PortfolioResult {
  total_value_tao: number;
  total_staked_tao: number;
  total_alpha_value_tao: number;
  positions: SubnetPosition[];
  subnets_exposed: number;
  coldkeys_resolved: number;
  last_updated: string;
  change_24h_pct: number | null;
  change_7d_pct: number | null;
}

/** A coldkey address with an optional user-assigned label */
export interface LabeledAddress {
  address: string;
  label: string;
}

/** Time range options for historical charts */
export type TimeRange = "7d" | "30d" | "90d";

/** A single data point in portfolio history */
export interface PortfolioHistoryPoint {
  time: string;
  total_value_tao: number;
}

/** Portfolio history response from engine */
export interface PortfolioHistoryResult {
  points: PortfolioHistoryPoint[];
  data_start: string | null;
  time_range: string;
}

/** Valid sort fields for screener queries */
export type ScreenerSortField =
  | "miner_count"
  | "validator_count"
  | "registration_cost"
  | "emission_share"
  | "alpha_price"
  | "alpha_market_cap"
  | "fill_rate"
  | "owner_take_rate"
  | "tao_reserves"
  | "alpha_reserves";

/** Screener filter criteria */
export interface ScreenerFilter {
  min_miners: number | null;
  max_miners: number | null;
  min_validators: number | null;
  max_validators: number | null;
  min_registration_cost: number | null;
  max_registration_cost: number | null;
  min_emission_share: number | null;
  max_emission_share: number | null;
  min_alpha_price: number | null;
  max_alpha_price: number | null;
  min_subnet_age_days: number | null;
  max_subnet_age_days: number | null;
  sort_by: ScreenerSortField;
  sort_direction: "asc" | "desc";
}

/** Per-subnet data for the screener table (matches Python ScreenerSubnetSchema) */
export interface ScreenerSubnet {
  netuid: number;
  name: string | null;
  miner_count: number;
  validator_count: number;
  registration_cost: number;
  emission_share: number;
  alpha_price: number;
  alpha_market_cap: number;
  fill_rate: number;
  owner_take_rate: number;
  tao_reserves: number;
  alpha_reserves: number;
  subnet_age_days: number;
  sparkline_emission_7d: number[];
  sparkline_price_7d: number[];
}

/** Screener query result (matches Python ScreenerResponseSchema) */
export interface ScreenerResult {
  subnets: ScreenerSubnet[];
  subnet_count: number;
}

/** Subnet detail — current snapshot with computed fields (matches Python SubnetDetailSchema) */
export interface SubnetDetail {
  netuid: number;
  name: string | null;
  miner_count: number;
  validator_count: number;
  registration_cost: number;
  emission_share: number;
  alpha_price: number;
  alpha_market_cap: number;
  tao_reserves: number;
  alpha_reserves: number;
  fill_rate: number;
  owner_take_rate: number;
  subnet_age_days: number;
  description: string | null;
}

/** Daily history point for subnet time-series charts */
export interface SubnetHistoryPoint {
  time: string;
  emission_share: number;
  alpha_price: number;
  miner_count: number;
}

/** Neuron (miner or validator) in a subnet */
export interface SubnetNeuron {
  uid: number;
  hotkey: string;
  coldkey: string;
  stake: number;
  incentive: number;
  trust: number;
  dividends: number;
  is_active: boolean;
}

/** Complete subnet detail response (matches Python SubnetDetailResponseSchema) */
export interface SubnetDetailResult {
  detail: SubnetDetail;
  history: SubnetHistoryPoint[];
  miners: SubnetNeuron[];
  validators: SubnetNeuron[];
}

/** Standard API response envelope from engine */
export interface EngineResponse<T> {
  data: T;
  meta: {
    last_updated: string;
    cache_hit: boolean;
    compute_ms: number;
  };
}

/** Standard error response */
export interface ErrorResponse {
  error: {
    type: string;
    message: string;
    code: number;
  };
}
