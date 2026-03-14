/**
 * Shared constants used across the Subtensor Labs monorepo.
 */

/** TAO denomination: 1 TAO = 10^9 rao */
export const RAO_PER_TAO = 1_000_000_000;

/** Post-halving emission rate: TAO per block */
export const EMISSION_PER_BLOCK = 0.5;

/** Approximate blocks per day (12s block time) */
export const BLOCKS_PER_DAY = 7_200;

/** Approximate TAO emitted per day post-halving */
export const TAO_PER_DAY = EMISSION_PER_BLOCK * BLOCKS_PER_DAY;

/** Default metagraph sync interval in seconds */
export const SYNC_INTERVAL_SECONDS = 120;

/** Default cache TTLs in seconds */
export const CACHE_TTL = {
  METAGRAPH: 180,
  PRICE: 180,
  PORTFOLIO: 300,
  SCREENER: 120,
} as const;

/** Subnet display names for well-known subnets */
export const SUBNET_NAMES: Record<number, string> = {
  0: "Root",
  1: "Text Prompting",
  2: "Machine Translation",
  3: "Data Scraping",
  4: "Multi Modality",
  5: "Image Generation",
  8: "Taoshi",
  9: "Pretraining",
  13: "Dataverse",
  18: "Cortex.t",
  19: "Vision",
  21: "FileTAO",
  22: "Datura",
  27: "Compute",
  32: "It's AI",
  34: "BitMind",
} as const;
