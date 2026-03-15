import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom";
import { ExploreAddressInput } from "./ExploreAddressInput";

const VALID_ADDRESS = "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty";

describe("ExploreAddressInput", () => {
  it("renders address input and submit button", () => {
    render(<ExploreAddressInput onSubmit={vi.fn()} isLoading={false} />);
    expect(screen.getByRole("textbox")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /view portfolio/i }),
    ).toBeInTheDocument();
  });

  it("submit button is disabled when input is empty", () => {
    render(<ExploreAddressInput onSubmit={vi.fn()} isLoading={false} />);
    expect(screen.getByRole("button", { name: /view portfolio/i })).toBeDisabled();
  });

  it("shows error for invalid SS58 address", async () => {
    const user = userEvent.setup();
    render(<ExploreAddressInput onSubmit={vi.fn()} isLoading={false} />);
    await user.type(screen.getByRole("textbox"), "not-a-valid-address");
    await user.click(screen.getByRole("button", { name: /view portfolio/i }));
    expect(screen.getByText(/invalid coldkey address/i)).toBeInTheDocument();
  });

  it("calls onSubmit with valid address", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<ExploreAddressInput onSubmit={onSubmit} isLoading={false} />);
    await user.type(screen.getByRole("textbox"), VALID_ADDRESS);
    await user.click(screen.getByRole("button", { name: /view portfolio/i }));
    expect(onSubmit).toHaveBeenCalledWith(VALID_ADDRESS);
  });

  it("supports Enter key submission", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<ExploreAddressInput onSubmit={onSubmit} isLoading={false} />);
    await user.type(screen.getByRole("textbox"), VALID_ADDRESS);
    await user.keyboard("{Enter}");
    expect(onSubmit).toHaveBeenCalledWith(VALID_ADDRESS);
  });

  it("submit button is disabled when isLoading is true", () => {
    render(<ExploreAddressInput onSubmit={vi.fn()} isLoading={true} />);
    expect(screen.getByRole("button", { name: /view portfolio/i })).toBeDisabled();
  });

  it("clears input after successful submission", async () => {
    const user = userEvent.setup();
    render(<ExploreAddressInput onSubmit={vi.fn()} isLoading={false} />);
    const input = screen.getByRole("textbox");
    await user.type(input, VALID_ADDRESS);
    await user.click(screen.getByRole("button", { name: /view portfolio/i }));
    expect(input).toHaveValue("");
  });
});
