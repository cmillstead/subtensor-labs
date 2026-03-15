import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect } from "vitest";
import { SubnetPositionList, SubnetPositionListSkeleton } from "./SubnetPositionList";
import type { SubnetPosition } from "@/types";

const HOTKEY_1 = "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty";
const HOTKEY_2 = "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY";

function mockPosition(overrides: Partial<SubnetPosition> = {}): SubnetPosition {
  return {
    netuid: 1,
    subnet_name: null,
    hotkey: HOTKEY_1,
    staked_tao: 100,
    alpha_holdings: 50,
    alpha_value_tao: 25,
    emission_share: 0.05,
    incentive: 0,
    trust: 0.9,
    dividends: 0.1,
    is_active: true,
    is_miner: false,
    delegations: [],
    ...overrides,
  };
}

const positionA = mockPosition({
  netuid: 1,
  subnet_name: "Alpha",
  hotkey: HOTKEY_1,
  staked_tao: 500,
  alpha_value_tao: 200,
  emission_share: 0.1,
});

const positionB = mockPosition({
  netuid: 3,
  subnet_name: "Beta",
  hotkey: HOTKEY_2,
  staked_tao: 100,
  alpha_value_tao: 50,
  emission_share: 0.2,
});

describe("SubnetPositionList", () => {
  it("renders empty state when no positions", () => {
    render(<SubnetPositionList positions={[]} />);
    expect(screen.getByText("No subnet positions found")).toBeInTheDocument();
  });

  it("renders a card for each position", () => {
    render(<SubnetPositionList positions={[positionA, positionB]} />);
    // Use aria-label which includes the subnet netuid
    expect(screen.getByLabelText(/Position in subnet 1 Alpha/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Position in subnet 3 Beta/)).toBeInTheDocument();
  });

  it("sorts by total value descending by default", () => {
    render(<SubnetPositionList positions={[positionB, positionA]} />);
    const cards = screen.getAllByLabelText(/Position in subnet/);
    // positionA has higher value (500+200=700) vs positionB (100+50=150)
    expect(cards[0]).toHaveAttribute(
      "aria-label",
      expect.stringContaining("subnet 1"),
    );
    expect(cards[1]).toHaveAttribute(
      "aria-label",
      expect.stringContaining("subnet 3"),
    );
  });

  it("changes sort order when dropdown is changed", async () => {
    const user = userEvent.setup();
    render(<SubnetPositionList positions={[positionA, positionB]} />);

    const select = screen.getByLabelText("Sort by");
    await user.selectOptions(select, "emission_share");

    const cards = screen.getAllByLabelText(/Position in subnet/);
    // positionB has higher emission (0.2) vs positionA (0.1)
    expect(cards[0]).toHaveAttribute(
      "aria-label",
      expect.stringContaining("subnet 3"),
    );
  });

  it("renders sort dropdown with all options", () => {
    render(<SubnetPositionList positions={[positionA]} />);
    const select = screen.getByLabelText("Sort by") as HTMLSelectElement;
    expect(select).toBeInTheDocument();
    const options = Array.from(select.options).map((o) => o.text);
    expect(options).toEqual([
      "Total Value",
      "Staked TAO",
      "Alpha Value",
      "Emission Share",
      "Subnet Name",
    ]);
  });
});

describe("SubnetPositionListSkeleton", () => {
  it("renders 3 skeleton cards", () => {
    render(<SubnetPositionListSkeleton />);
    const skeletons = screen.getAllByLabelText("Loading subnet position");
    expect(skeletons).toHaveLength(3);
  });
});
