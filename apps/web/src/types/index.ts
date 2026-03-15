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
  EngineResponse,
  ErrorResponse,
} from "@subtensor-labs/shared";

/** Navigation route definition for the app shell */
export interface NavRoute {
  href: string;
  label: string;
}

/** Ticker bar data from engine health/market endpoint */
export interface TickerData {
  tao_price_usd: number | null;
  market_cap_usd: number | null;
  current_block: number | null;
}
