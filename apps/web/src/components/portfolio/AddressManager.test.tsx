import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { AddressManager } from "./AddressManager";

// SS58 addresses: 46-48 base58 characters (no 0, O, I, l)
const VALID_ADDRESS = "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty";
const VALID_ADDRESS_2 = "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY";

describe("AddressManager", () => {
  it("renders address input and add button", () => {
    render(<AddressManager addresses={[]} onAddressesChange={vi.fn()} />);
    expect(screen.getByLabelText(/coldkey address input/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /add address/i }),
    ).toBeInTheDocument();
  });

  it("adds a valid SS58 address", () => {
    const onChange = vi.fn();
    render(<AddressManager addresses={[]} onAddressesChange={onChange} />);

    const input = screen.getByLabelText(/coldkey address input/i);
    fireEvent.change(input, { target: { value: VALID_ADDRESS } });
    fireEvent.click(screen.getByRole("button", { name: /add address/i }));

    expect(onChange).toHaveBeenCalledWith([VALID_ADDRESS]);
  });

  it("rejects invalid address format", () => {
    const onChange = vi.fn();
    render(<AddressManager addresses={[]} onAddressesChange={onChange} />);

    const input = screen.getByLabelText(/coldkey address input/i);
    fireEvent.change(input, { target: { value: "invalid" } });
    fireEvent.click(screen.getByRole("button", { name: /add address/i }));

    expect(onChange).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent(/invalid ss58/i);
  });

  it("rejects duplicate addresses", () => {
    const onChange = vi.fn();
    render(
      <AddressManager
        addresses={[VALID_ADDRESS]}
        onAddressesChange={onChange}
      />,
    );

    const input = screen.getByLabelText(/coldkey address input/i);
    fireEvent.change(input, { target: { value: VALID_ADDRESS } });
    fireEvent.click(screen.getByRole("button", { name: /add address/i }));

    expect(onChange).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent(/already added/i);
  });

  it("displays added addresses", () => {
    render(
      <AddressManager
        addresses={[VALID_ADDRESS]}
        onAddressesChange={vi.fn()}
      />,
    );
    expect(screen.getByText(VALID_ADDRESS)).toBeInTheDocument();
  });

  it("removes an address when X is clicked", () => {
    const onChange = vi.fn();
    render(
      <AddressManager
        addresses={[VALID_ADDRESS, VALID_ADDRESS_2]}
        onAddressesChange={onChange}
      />,
    );

    const removeButtons = screen.getAllByRole("button", {
      name: /remove address/i,
    });
    fireEvent.click(removeButtons[0]);

    expect(onChange).toHaveBeenCalledWith([VALID_ADDRESS_2]);
  });

  it("adds address on Enter key", () => {
    const onChange = vi.fn();
    render(<AddressManager addresses={[]} onAddressesChange={onChange} />);

    const input = screen.getByLabelText(/coldkey address input/i);
    fireEvent.change(input, { target: { value: VALID_ADDRESS } });
    fireEvent.keyDown(input, { key: "Enter" });

    expect(onChange).toHaveBeenCalledWith([VALID_ADDRESS]);
  });

  it("shows error for empty input", () => {
    render(<AddressManager addresses={[]} onAddressesChange={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /add address/i }));
    expect(screen.getByRole("alert")).toHaveTextContent(
      /please enter a coldkey/i,
    );
  });

  it("clears input after successful add", () => {
    render(<AddressManager addresses={[]} onAddressesChange={vi.fn()} />);

    const input = screen.getByLabelText(
      /coldkey address input/i,
    ) as HTMLInputElement;
    fireEvent.change(input, { target: { value: VALID_ADDRESS } });
    fireEvent.click(screen.getByRole("button", { name: /add address/i }));

    expect(input.value).toBe("");
  });
});
