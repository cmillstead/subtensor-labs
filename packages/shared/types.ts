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
  | "alpha_reserves"
  | "alpha_price_change_24h"
  | "alpha_price_change_7d"
  | "alpha_price_change_30d"
  | "net_tao_inflow"
  | "immunity_active";

/** Screener filter criteria */
export interface ScreenerFilter {
  // Basic filters (free tier)
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
  // Advanced filters (premium)
  min_alpha_price_change_24h: number | null;
  max_alpha_price_change_24h: number | null;
  min_alpha_price_change_7d: number | null;
  max_alpha_price_change_7d: number | null;
  min_alpha_price_change_30d: number | null;
  max_alpha_price_change_30d: number | null;
  min_alpha_market_cap: number | null;
  max_alpha_market_cap: number | null;
  min_net_tao_inflow: number | null;
  max_net_tao_inflow: number | null;
  min_fill_rate: number | null;
  max_fill_rate: number | null;
  min_owner_take_rate: number | null;
  max_owner_take_rate: number | null;
  immunity_active: boolean | null;
  // Sort
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
  alpha_price_change_24h: number | null;
  alpha_price_change_7d: number | null;
  alpha_price_change_30d: number | null;
  net_tao_inflow: number | null;
  immunity_active: boolean;
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

/** Time horizon for yield projections */
export type PredictionHorizon = 30 | 60 | 90;

/** A single point in the yield projection time-series chart */
export interface YieldChartPoint {
  day: number;
  projected_yield_tao: number;
  confidence_68_lower: number;
  confidence_68_upper: number;
  confidence_95_lower: number;
  confidence_95_upper: number;
}

/** Yield projection for a single subnet at a given horizon */
export interface SubnetYieldProjection {
  netuid: number;
  subnet_name: string | null;
  current_stake_tao: number;
  projected_yield_tao: number;
  emission_trend_slope: number;
  r_squared: number;
  confidence_68_lower: number;
  confidence_68_upper: number;
  confidence_95_lower: number;
  confidence_95_upper: number;
  has_volatility_warning: boolean;
}

/** Aggregated yield projection for a specific time horizon */
export interface HorizonProjection {
  horizon_days: number;
  total_projected_yield_tao: number;
  total_confidence_68_lower: number;
  total_confidence_68_upper: number;
  total_confidence_95_lower: number;
  total_confidence_95_upper: number;
  subnet_projections: SubnetYieldProjection[];
}

/** Complete yield projection response (matches Python YieldProjectionResponseSchema) */
export interface YieldProjectionResult {
  projections: HorizonProjection[];
  chart_data: YieldChartPoint[];
  caveat: string;
  last_computed: string;
  total_staked_tao: number;
  subnets_analyzed: number;
  subnets_skipped: number;
}

/** Saved screener configuration (matches Python SavedScreenerResponseSchema) */
export interface SavedScreener {
  id: number;
  name: string;
  filters_json: ScreenerFilter;
  created_at: string;
  updated_at: string;
}

/** A single TAO rebalancing move within a scenario */
export interface ScenarioMove {
  source_netuid: number;
  dest_netuid: number;
  amount_tao: number;
}

/** A single scenario with a label and moves */
export interface ScenarioInput {
  label: string | null;
  moves: ScenarioMove[];
}

/** Request for scenario comparison calculation */
export interface ScenarioCalcRequest {
  coldkey_addresses: string[];
  scenarios: ScenarioInput[];
  horizon: number;
}

/** Per-subnet allocation and yield within a scenario outcome */
export interface SubnetAllocation {
  netuid: number;
  stake_tao: number;
  allocation_pct: number;
  projected_yield_tao: number;
  confidence_68_lower: number;
  confidence_68_upper: number;
  alpha_price: number | null;
  alpha_exposure_tao: number | null;
}

/** Full outcome for a single scenario (or the baseline) */
export interface ScenarioOutcome {
  label: string | null;
  allocations: SubnetAllocation[];
  total_staked_tao: number;
  total_projected_yield_tao: number;
  total_confidence_68_lower: number;
  total_confidence_68_upper: number;
  total_alpha_exposure_tao: number;
  hhi: number;
  yield_delta_tao: number;
  yield_delta_pct: number;
}

/** Complete scenario comparison response */
export interface ScenarioComparisonResult {
  baseline: ScenarioOutcome;
  scenarios: ScenarioOutcome[];
  best_yield_index: number;
  best_diversification_index: number;
  horizon_days: number;
  caveat: string;
  last_computed: string;
}
