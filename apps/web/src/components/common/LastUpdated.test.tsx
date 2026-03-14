import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { LastUpdated } from "./LastUpdated";

describe("LastUpdated", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-03-14T15:00:00Z"));
  });

  it("renders 'just now' for timestamps less than 1 minute ago", () => {
    render(<LastUpdated timestamp="2026-03-14T14:59:30Z" />);
    expect(screen.getByText(/just now/i)).toBeInTheDocument();
  });

  it("renders minutes ago", () => {
    render(<LastUpdated timestamp="2026-03-14T14:57:00Z" />);
    expect(screen.getByText(/3 min ago/i)).toBeInTheDocument();
  });

  it("renders hours ago", () => {
    render(<LastUpdated timestamp="2026-03-14T13:00:00Z" />);
    expect(screen.getByText(/2 hr ago/i)).toBeInTheDocument();
  });

  it("has accessible label", () => {
    render(<LastUpdated timestamp="2026-03-14T14:57:00Z" />);
    expect(screen.getByLabelText(/last updated/i)).toBeInTheDocument();
  });

  afterEach(() => {
    vi.useRealTimers();
  });
});
