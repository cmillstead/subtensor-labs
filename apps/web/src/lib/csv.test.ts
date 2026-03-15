import { describe, it, expect } from "vitest";
import { generatePortfolioCsv, generatePortfolioFilename } from "./csv";
import type { PortfolioResult, SubnetPosition } from "@/types";

function makePosition(overrides: Partial<SubnetPosition> = {}): SubnetPosition {
  return {
    netuid: 1,
    subnet_name: "Alpha",
    hotkey: "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty",
    staked_tao: 100.5,
    alpha_holdings: 50.25,
    alpha_value_tao: 25.125,
    emission_share: 0.035,
    incentive: 0,
    trust: 0,
    dividends: 0,
    is_active: true,
    is_miner: false,
    delegations: [],
    ...overrides,
  };
}

function makeResult(overrides: Partial<PortfolioResult> = {}): PortfolioResult {
  return {
    total_value_tao: 200,
    free_balance_tao: 10,
    staked_tao: 150,
    alpha_value_tao: 40,
    positions: [],
    addresses: ["5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty"],
    last_updated: "2026-03-14T12:00:00Z",
    change_24h_pct: 2.5,
    change_7d_pct: -1.3,
    ...overrides,
  };
}

const EXPECTED_HEADER =
  "subnet_name,netuid,staked_tao,alpha_holdings,alpha_value_tao,emission_share_pct,is_miner,incentive,trust,dividends,validator_name,delegation_amount_tao,delegation_apy_pct,delegation_take_rate_pct";

describe("generatePortfolioCsv", () => {
  it("generates correct header row", () => {
    const csv = generatePortfolioCsv(makeResult());
    const lines = csv.split("\n");
    expect(lines[0]).toBe(EXPECTED_HEADER);
  });

  it("returns header-only for empty positions", () => {
    const csv = generatePortfolioCsv(makeResult({ positions: [] }));
    const lines = csv.split("\n").filter((l) => l.length > 0);
    expect(lines).toHaveLength(1);
    expect(lines[0]).toBe(EXPECTED_HEADER);
  });

  it("flattens subnet positions into rows with correct values", () => {
    const csv = generatePortfolioCsv(
      makeResult({
        positions: [makePosition()],
      }),
    );
    const lines = csv.split("\n").filter((l) => l.length > 0);
    expect(lines).toHaveLength(2);
    const values = lines[1].split(",");
    expect(values[0]).toBe("Alpha"); // subnet_name
    expect(values[1]).toBe("1"); // netuid
    expect(values[2]).toBe("100.5"); // staked_tao
    expect(values[3]).toBe("50.25"); // alpha_holdings (alpha_holdings)
    expect(values[4]).toBe("25.125"); // alpha_value_tao
    expect(values[5]).toBe("3.5"); // emission_share_pct (0.035 * 100)
    expect(values[6]).toBe("false"); // is_miner
  });

  it("includes delegation detail rows per subnet", () => {
    const csv = generatePortfolioCsv(
      makeResult({
        positions: [
          makePosition({
            delegations: [
              {
                validator_hotkey: "5abc",
                validator_name: "Validator A",
                delegated_amount: 50,
                estimated_apy: 12.5,
                take_rate: 0.18,
              },
              {
                validator_hotkey: "5def",
                validator_name: "Validator B",
                delegated_amount: 30,
                estimated_apy: 10.0,
                take_rate: 0.1,
              },
            ],
          }),
        ],
      }),
    );
    const lines = csv.split("\n").filter((l) => l.length > 0);
    // 1 header + 1 position row + 2 delegation rows
    expect(lines).toHaveLength(4);

    // First delegation row
    const del1 = lines[2].split(",");
    expect(del1[0]).toBe("Alpha"); // subnet_name repeated
    expect(del1[1]).toBe("1"); // netuid repeated
    expect(del1[10]).toBe("Validator A");
    expect(del1[11]).toBe("50");
    expect(del1[12]).toBe("12.5");
    expect(del1[13]).toBe("18"); // take_rate 0.18 * 100

    // Second delegation row
    const del2 = lines[3].split(",");
    expect(del2[10]).toBe("Validator B");
    expect(del2[11]).toBe("30");
    expect(del2[13]).toBe("10"); // take_rate 0.1 * 100
  });

  it("handles miner positions with incentive/trust/dividends", () => {
    const csv = generatePortfolioCsv(
      makeResult({
        positions: [
          makePosition({
            is_miner: true,
            incentive: 0.85,
            trust: 0.92,
            dividends: 0.15,
          }),
        ],
      }),
    );
    const lines = csv.split("\n").filter((l) => l.length > 0);
    const values = lines[1].split(",");
    expect(values[6]).toBe("true");
    expect(values[7]).toBe("0.85");
    expect(values[8]).toBe("0.92");
    expect(values[9]).toBe("0.15");
  });

  it("formats TAO amounts as plain numbers", () => {
    const csv = generatePortfolioCsv(
      makeResult({
        positions: [
          makePosition({ staked_tao: 1234.56789 }),
        ],
      }),
    );
    const lines = csv.split("\n").filter((l) => l.length > 0);
    const values = lines[1].split(",");
    // Must be plain number, no commas, no currency symbols
    expect(values[2]).toBe("1234.56789");
    expect(values[2]).not.toContain("$");
    expect(values[2]).not.toContain("TAO");
  });

  it("handles null/undefined fields as empty strings", () => {
    const csv = generatePortfolioCsv(
      makeResult({
        positions: [
          makePosition({
            subnet_name: null,
            delegations: [
              {
                validator_hotkey: "5abc",
                validator_name: null,
                delegated_amount: 50,
                estimated_apy: null,
                take_rate: 0.1,
              },
            ],
          }),
        ],
      }),
    );
    const lines = csv.split("\n").filter((l) => l.length > 0);
    // Position row: subnet_name is null → empty
    expect(lines[1].split(",")[0]).toBe("");
    // Delegation row: validator_name null → empty, apy null → empty
    const del = lines[2].split(",");
    expect(del[10]).toBe(""); // validator_name
    expect(del[12]).toBe(""); // delegation_apy_pct
  });

  it("escapes commas in field values", () => {
    const csv = generatePortfolioCsv(
      makeResult({
        positions: [
          makePosition({ subnet_name: "Alpha, Beta" }),
        ],
      }),
    );
    const lines = csv.split("\n").filter((l) => l.length > 0);
    // Field with comma should be quoted
    expect(lines[1]).toContain('"Alpha, Beta"');
  });
});

describe("generatePortfolioFilename", () => {
  it("includes date in YYYY-MM-DD format", () => {
    const filename = generatePortfolioFilename();
    expect(filename).toMatch(
      /^subtensor-labs-portfolio-\d{4}-\d{2}-\d{2}\.csv$/,
    );
  });
});
