import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { SubnetNeuronTable } from "./SubnetNeuronTable";
import type { SubnetNeuron } from "@/types";

const mockNeurons: SubnetNeuron[] = [
  {
    uid: 1,
    hotkey: "5FHneW46xGXgs8reC1234",
    coldkey: "5GrwvaEF5zXb26qYaa99",
    stake: 1234.56,
    incentive: 0.95,
    trust: 0.88,
    dividends: 0.0,
    is_active: true,
  },
  {
    uid: 2,
    hotkey: "5DAAnrj7VHTzDs7a5678",
    coldkey: "5FLSigC9HGRKVh9b1234",
    stake: 567.89,
    incentive: 0.42,
    trust: 0.75,
    dividends: 0.0,
    is_active: false,
  },
];

describe("SubnetNeuronTable", () => {
  it("renders table title", () => {
    render(<SubnetNeuronTable neurons={mockNeurons} title="Top Miners" />);
    expect(screen.getByText("Top Miners")).toBeInTheDocument();
  });

  it("renders column headers", () => {
    render(<SubnetNeuronTable neurons={mockNeurons} title="Top Miners" />);
    expect(screen.getByText("UID")).toBeInTheDocument();
    expect(screen.getByText("Hotkey")).toBeInTheDocument();
    expect(screen.getByText("Stake (τ)")).toBeInTheDocument();
    expect(screen.getByText("Incentive")).toBeInTheDocument();
    expect(screen.getByText("Trust")).toBeInTheDocument();
    expect(screen.getByText("Status")).toBeInTheDocument();
  });

  it("renders neuron UIDs", () => {
    render(<SubnetNeuronTable neurons={mockNeurons} title="Top Miners" />);
    expect(screen.getByText("1")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
  });

  it("renders truncated hotkeys", () => {
    render(<SubnetNeuronTable neurons={mockNeurons} title="Top Miners" />);
    // "5FHneW46xGXgs8reC1234" (21 chars) → first 6 + "..." + last 6
    expect(screen.getByText("5FHneW...eC1234")).toBeInTheDocument();
    // "5DAAnrj7VHTzDs7a5678" (20 chars) → first 6 + "..." + last 6
    expect(screen.getByText("5DAAnr...7a5678")).toBeInTheDocument();
  });

  it("renders active status badge", () => {
    render(<SubnetNeuronTable neurons={mockNeurons} title="Top Miners" />);
    expect(screen.getByText("Active")).toBeInTheDocument();
  });

  it("renders inactive status badge", () => {
    render(<SubnetNeuronTable neurons={mockNeurons} title="Top Miners" />);
    expect(screen.getByText("Inactive")).toBeInTheDocument();
  });

  it("renders incentive values", () => {
    render(<SubnetNeuronTable neurons={mockNeurons} title="Top Miners" />);
    expect(screen.getByText("0.9500")).toBeInTheDocument();
    expect(screen.getByText("0.4200")).toBeInTheDocument();
  });

  it("renders trust values", () => {
    render(<SubnetNeuronTable neurons={mockNeurons} title="Top Miners" />);
    expect(screen.getByText("0.8800")).toBeInTheDocument();
    expect(screen.getByText("0.7500")).toBeInTheDocument();
  });

  it("shows empty state when no neurons", () => {
    render(<SubnetNeuronTable neurons={[]} title="Top Validators" />);
    expect(screen.getByText("Top Validators")).toBeInTheDocument();
    expect(screen.getByText("No data available.")).toBeInTheDocument();
  });
});
