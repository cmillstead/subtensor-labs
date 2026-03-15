import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { SubnetMetrics } from "./SubnetMetrics";
import type { SubnetDetail } from "@/types";

const mockDetail: SubnetDetail = {
  netuid: 1,
  name: "Text Prompting",
  miner_count: 100,
  validator_count: 50,
  registration_cost: 1.5,
  emission_share: 0.05,
  alpha_price: 0.12,
  alpha_market_cap: 1200.0,
  tao_reserves: 500.0,
  alpha_reserves: 4000.0,
  fill_rate: 0.78,
  owner_take_rate: 0.18,
  subnet_age_days: 120,
  description: null,
};

describe("SubnetMetrics", () => {
  it("renders miner count", () => {
    render(<SubnetMetrics detail={mockDetail} />);
    expect(screen.getByText("Miner Count")).toBeInTheDocument();
    expect(screen.getByText("100")).toBeInTheDocument();
  });

  it("renders validator count", () => {
    render(<SubnetMetrics detail={mockDetail} />);
    expect(screen.getByText("Validator Count")).toBeInTheDocument();
    expect(screen.getByText("50")).toBeInTheDocument();
  });

  it("renders registration cost with TaoAmount", () => {
    render(<SubnetMetrics detail={mockDetail} />);
    expect(screen.getByText("Registration Cost")).toBeInTheDocument();
    expect(screen.getByLabelText(/1\.50 TAO/)).toBeInTheDocument();
  });

  it("renders emission share as percentage", () => {
    render(<SubnetMetrics detail={mockDetail} />);
    expect(screen.getByText("Emission Share")).toBeInTheDocument();
    expect(screen.getByText("5.00%")).toBeInTheDocument();
  });

  it("renders alpha price with TaoAmount", () => {
    render(<SubnetMetrics detail={mockDetail} />);
    expect(screen.getByText("Alpha Price")).toBeInTheDocument();
    expect(screen.getByLabelText(/0\.12 TAO/)).toBeInTheDocument();
  });

  it("renders market cap with TaoAmount abbreviated", () => {
    render(<SubnetMetrics detail={mockDetail} />);
    expect(screen.getByText("Market Cap")).toBeInTheDocument();
    expect(screen.getByLabelText(/1,200\.00 TAO/)).toBeInTheDocument();
  });

  it("renders fill rate as percentage", () => {
    render(<SubnetMetrics detail={mockDetail} />);
    expect(screen.getByText("Fill Rate")).toBeInTheDocument();
    expect(screen.getByText("78.00%")).toBeInTheDocument();
  });

  it("renders owner take rate as percentage", () => {
    render(<SubnetMetrics detail={mockDetail} />);
    expect(screen.getByText("Owner Take Rate")).toBeInTheDocument();
    expect(screen.getByText("18.00%")).toBeInTheDocument();
  });

  it("renders subnet age in days", () => {
    render(<SubnetMetrics detail={mockDetail} />);
    expect(screen.getByText("Subnet Age")).toBeInTheDocument();
    expect(screen.getByText("120 days")).toBeInTheDocument();
  });

  it("renders singular 'day' for age of 1", () => {
    render(<SubnetMetrics detail={{ ...mockDetail, subnet_age_days: 1 }} />);
    expect(screen.getByText("1 day")).toBeInTheDocument();
  });

  it("renders all 10 metric cards", () => {
    render(<SubnetMetrics detail={mockDetail} />);
    const labels = [
      "Miner Count", "Validator Count", "Registration Cost",
      "Emission Share", "Alpha Price", "Market Cap",
      "TAO Reserves", "Fill Rate", "Owner Take Rate", "Subnet Age",
    ];
    for (const label of labels) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
  });
});
