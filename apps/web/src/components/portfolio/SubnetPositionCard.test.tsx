import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect } from "vitest";
import { SubnetPositionCard, SubnetPositionSkeleton } from "./SubnetPositionCard";
import type { SubnetPosition } from "@/types";

const HOTKEY = "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty";

function mockPosition(overrides: Partial<SubnetPosition> = {}): SubnetPosition {
  return {
    netuid: 3,
    subnet_name: "Templar",
    hotkey: HOTKEY,
    staked_tao: 450.0,
    alpha_holdings: 12500,
    alpha_value_tao: 171.0,
    emission_share: 0.058,
    incentive: 0,
    trust: 0.9,
    dividends: 0.1,
    is_active: true,
    is_miner: false,
    delegations: [
      {
        validator_hotkey: HOTKEY,
        validator_name: "MyValidator",
        delegated_amount: 450.0,
        estimated_apy: 8.2,
        take_rate: 0.18,
      },
    ],
    ...overrides,
  };
}

describe("SubnetPositionCard", () => {
  it("renders subnet name and netuid", () => {
    render(<SubnetPositionCard position={mockPosition()} />);
    expect(screen.getByText("SN3")).toBeInTheDocument();
    expect(screen.getByText(/Templar/)).toBeInTheDocument();
  });

  it("renders fallback name when subnet_name is null", () => {
    render(<SubnetPositionCard position={mockPosition({ subnet_name: null })} />);
    expect(screen.getByText("SN3")).toBeInTheDocument();
    expect(screen.queryByText(/Templar/)).not.toBeInTheDocument();
  });

  it("renders staked TAO amount", () => {
    render(<SubnetPositionCard position={mockPosition()} />);
    expect(screen.getByText("Staked")).toBeInTheDocument();
    // Multiple TaoAmount with 450.00 exist (staked + delegation), verify at least one is present
    const taoLabels = screen.getAllByLabelText("450.00 TAO");
    expect(taoLabels.length).toBeGreaterThanOrEqual(1);
  });

  it("renders alpha holdings", () => {
    render(<SubnetPositionCard position={mockPosition()} />);
    expect(screen.getByText("Alpha")).toBeInTheDocument();
    expect(screen.getByText(/12,500/)).toBeInTheDocument();
  });

  it("renders emission share percentage", () => {
    render(<SubnetPositionCard position={mockPosition()} />);
    // 0.058 * 100 = 5.8% — shown as plain percentage
    expect(screen.getByLabelText(/5\.8% emission share/)).toBeInTheDocument();
  });

  it("renders APY when delegation has estimated_apy", () => {
    render(<SubnetPositionCard position={mockPosition()} />);
    expect(screen.getByText(/8\.2% APY/)).toBeInTheDocument();
  });

  it("has accessible aria-label with value", () => {
    render(<SubnetPositionCard position={mockPosition()} />);
    expect(
      screen.getByLabelText(/Position in subnet 3 Templar worth/),
    ).toBeInTheDocument();
  });

  it("shows Miner badge when is_miner is true", () => {
    render(
      <SubnetPositionCard position={mockPosition({ is_miner: true, incentive: 0.5 })} />,
    );
    expect(screen.getByText("Miner")).toBeInTheDocument();
  });

  it("does not show Miner badge when is_miner is false", () => {
    render(<SubnetPositionCard position={mockPosition({ is_miner: false })} />);
    expect(screen.queryByText("Miner")).not.toBeInTheDocument();
  });

  it("shows Inactive badge when is_active is false", () => {
    render(
      <SubnetPositionCard position={mockPosition({ is_active: false })} />,
    );
    expect(screen.getByText("Inactive")).toBeInTheDocument();
  });
});

describe("SubnetPositionCard drill-down", () => {
  it("is collapsed by default", () => {
    render(<SubnetPositionCard position={mockPosition()} />);
    const button = screen.getByRole("button");
    expect(button).toHaveAttribute("aria-expanded", "false");
    expect(button).toHaveAttribute("data-state", "closed");
  });

  it("expands on click showing delegation details", async () => {
    const user = userEvent.setup();
    render(<SubnetPositionCard position={mockPosition()} />);
    const button = screen.getByRole("button");

    await user.click(button);

    expect(button).toHaveAttribute("aria-expanded", "true");
    expect(button).toHaveAttribute("data-state", "open");
    expect(screen.getByText("MyValidator")).toBeInTheDocument();
    expect(screen.getByText("18.0%")).toBeInTheDocument(); // take rate
  });

  it("shows no delegations message when empty", async () => {
    const user = userEvent.setup();
    render(
      <SubnetPositionCard position={mockPosition({ delegations: [] })} />,
    );

    await user.click(screen.getByRole("button"));
    expect(
      screen.getByText("No delegation details available"),
    ).toBeInTheDocument();
  });

  it("shows emission share in drill-down", async () => {
    const user = userEvent.setup();
    render(<SubnetPositionCard position={mockPosition()} />);

    await user.click(screen.getByRole("button"));
    expect(screen.getByText("Emission Share")).toBeInTheDocument();
  });
});

describe("SubnetPositionCard miner details", () => {
  it("shows miner details section when is_miner and expanded", async () => {
    const user = userEvent.setup();
    render(
      <SubnetPositionCard
        position={mockPosition({
          is_miner: true,
          incentive: 0.5,
          trust: 0.85,
          dividends: 12.5,
        })}
      />,
    );

    await user.click(screen.getByRole("button"));

    expect(screen.getByText("Miner Details")).toBeInTheDocument();
    expect(screen.getByText("Incentive")).toBeInTheDocument();
    expect(screen.getByText("50.0%")).toBeInTheDocument(); // incentive
    expect(screen.getByText("85.0%")).toBeInTheDocument(); // trust
  });

  it("does not show miner details when is_miner is false", async () => {
    const user = userEvent.setup();
    render(<SubnetPositionCard position={mockPosition({ is_miner: false })} />);

    await user.click(screen.getByRole("button"));
    expect(screen.queryByText("Miner Details")).not.toBeInTheDocument();
  });

  it("shows both miner badge and delegation details", async () => {
    const user = userEvent.setup();
    render(
      <SubnetPositionCard
        position={mockPosition({ is_miner: true, incentive: 0.3 })}
      />,
    );

    await user.click(screen.getByRole("button"));
    expect(screen.getByText("Miner Details")).toBeInTheDocument();
    expect(screen.getByText("Delegations")).toBeInTheDocument();
    expect(screen.getByText("MyValidator")).toBeInTheDocument();
  });
});

describe("SubnetPositionSkeleton", () => {
  it("renders loading state with aria-label", () => {
    render(<SubnetPositionSkeleton />);
    expect(
      screen.getByLabelText("Loading subnet position"),
    ).toBeInTheDocument();
  });

  it("has animate-pulse class", () => {
    const { container } = render(<SubnetPositionSkeleton />);
    expect(container.firstChild).toHaveClass("animate-pulse");
  });
});
