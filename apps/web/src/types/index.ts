export type {
  SubnetSnapshot,
  AlphaPrice,
  SubnetPosition,
  DelegationDetail,
  PortfolioResult,
  LabeledAddress,
  PortfolioHistoryPoint,
  PortfolioHistoryResult,
  TimeRange,
  ScreenerFilter,
  ScreenerSortField,
  ScreenerSubnet,
  ScreenerResult,
  SubnetDetail,
  SubnetHistoryPoint,
  SubnetNeuron,
  SubnetDetailResult,
  EngineResponse,
  ErrorResponse,
} from "@subtensor-labs/shared";

/** Navigation route definition for the app shell */
export interface NavRoute {
  href: string;
  label: string;
}

/** A server-persisted address with database ID */
export interface ServerAddress {
  id: number;
  coldkey_address: string;
  label: string | null;
  is_watch_only: boolean;
  created_at: string;
}

/** Ticker bar data from engine health/market endpoint */
export interface TickerData {
  tao_price_usd: number | null;
  market_cap_usd: number | null;
  current_block: number | null;
}
