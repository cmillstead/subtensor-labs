import { describe, it, expect } from "vitest";
import { generateScreenerCsv, generateScreenerFilename } from "./csv";
import type { ScreenerSubnet } from "@/types";

function makeSubnet(overrides: Partial<ScreenerSubnet> = {}): ScreenerSubnet {
  return {
    netuid: 1,
    name: "Text Prompting",
    miner_count: 120,
    validator_count: 24,
    registration_cost: 1000.5,
    emission_share: 0.05,
    alpha_price: 2.3,
    alpha_market_cap: 50000,
    fill_rate: 0.95,
    owner_take_rate: 0.18,
    tao_reserves: 100000,
    alpha_reserves: 500000,
    subnet_age_days: 365,
    sparkline_emission_7d: [0.04, 0.045, 0.05],
    sparkline_price_7d: [2.1, 2.2, 2.3],
    ...overrides,
  };
}

const EXPECTED_HEADER =
  "netuid,name,miner_count,validator_count,registration_cost,emission_share_pct,alpha_price,alpha_market_cap,fill_rate_pct,owner_take_rate_pct,tao_reserves,alpha_reserves,subnet_age_days";

describe("generateScreenerCsv", () => {
  it("generates correct header row", () => {
    const csv = generateScreenerCsv([]);
    const lines = csv.split("\n");
    expect(lines[0]).toBe(EXPECTED_HEADER);
  });

  it("returns header-only for empty subnets array", () => {
    const csv = generateScreenerCsv([]);
    const lines = csv.split("\n").filter((l) => l.length > 0);
    expect(lines).toHaveLength(1);
  });

  it("generates correct row values", () => {
    const csv = generateScreenerCsv([makeSubnet()]);
    const lines = csv.split("\n").filter((l) => l.length > 0);
    expect(lines).toHaveLength(2);
    const values = lines[1].split(",");
    expect(values[0]).toBe("1"); // netuid
    expect(values[1]).toBe("Text Prompting"); // name
    expect(values[2]).toBe("120"); // miner_count
    expect(values[3]).toBe("24"); // validator_count
    expect(values[4]).toBe("1000.5"); // registration_cost
    expect(values[5]).toBe("5"); // emission_share * 100
    expect(values[6]).toBe("2.3"); // alpha_price
    expect(values[7]).toBe("50000"); // alpha_market_cap
    expect(values[8]).toBe("95"); // fill_rate * 100
    expect(values[9]).toBe("18"); // owner_take_rate * 100
    expect(values[10]).toBe("100000"); // tao_reserves
    expect(values[11]).toBe("500000"); // alpha_reserves
    expect(values[12]).toBe("365"); // subnet_age_days
  });

  it("handles multiple subnets", () => {
    const csv = generateScreenerCsv([
      makeSubnet({ netuid: 1, name: "Alpha" }),
      makeSubnet({ netuid: 23, name: "NicheImage" }),
      makeSubnet({ netuid: 64, name: "Chutes" }),
    ]);
    const lines = csv.split("\n").filter((l) => l.length > 0);
    expect(lines).toHaveLength(4);
    expect(lines[1].split(",")[0]).toBe("1");
    expect(lines[2].split(",")[0]).toBe("23");
    expect(lines[3].split(",")[0]).toBe("64");
  });

  it("handles null subnet name as empty string", () => {
    const csv = generateScreenerCsv([makeSubnet({ name: null })]);
    const lines = csv.split("\n").filter((l) => l.length > 0);
    const values = lines[1].split(",");
    expect(values[1]).toBe("");
  });

  it("escapes commas in subnet names", () => {
    const csv = generateScreenerCsv([
      makeSubnet({ name: "Alpha, Beta" }),
    ]);
    const lines = csv.split("\n").filter((l) => l.length > 0);
    expect(lines[1]).toContain('"Alpha, Beta"');
  });

  it("escapes double quotes in subnet names", () => {
    const csv = generateScreenerCsv([
      makeSubnet({ name: 'The "Best" Subnet' }),
    ]);
    const lines = csv.split("\n").filter((l) => l.length > 0);
    expect(lines[1]).toContain('"The ""Best"" Subnet"');
  });

  it("formats TAO amounts as plain numbers", () => {
    const csv = generateScreenerCsv([
      makeSubnet({ registration_cost: 1234.56789 }),
    ]);
    const lines = csv.split("\n").filter((l) => l.length > 0);
    const values = lines[1].split(",");
    expect(values[4]).toBe("1234.56789");
    expect(values[4]).not.toContain("$");
    expect(values[4]).not.toContain("TAO");
  });

  it("does not include sparkline data in CSV columns", () => {
    const csv = generateScreenerCsv([makeSubnet()]);
    const header = csv.split("\n")[0];
    expect(header).not.toContain("sparkline");
  });
});

describe("generateScreenerFilename", () => {
  it("includes date in YYYY-MM-DD format", () => {
    const filename = generateScreenerFilename();
    expect(filename).toMatch(
      /^subtensor-labs-screener-\d{4}-\d{2}-\d{2}\.csv$/,
    );
  });

  it("starts with subtensor-labs-screener prefix", () => {
    const filename = generateScreenerFilename();
    expect(filename).toMatch(/^subtensor-labs-screener-/);
  });
});
