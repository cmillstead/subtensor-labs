import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { AddressManager } from "./AddressManager";
import type { LabeledAddress } from "@/types";

// SS58 addresses: 46-48 base58 characters (no 0, O, I, l)
const VALID_ADDRESS = "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty";
const VALID_ADDRESS_2 = "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY";

const labeled = (address: string, label = ""): LabeledAddress => ({
  address,
  label,
});

describe("AddressManager", () => {
  it("renders address input, label input, and add button", () => {
    render(<AddressManager addresses={[]} onAddressesChange={vi.fn()} />);
    expect(screen.getByLabelText(/coldkey address input/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/address label/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /add address/i }),
    ).toBeInTheDocument();
  });

  it("adds a valid SS58 address with no label", () => {
    const onChange = vi.fn();
    render(<AddressManager addresses={[]} onAddressesChange={onChange} />);

    const input = screen.getByLabelText(/coldkey address input/i);
    fireEvent.change(input, { target: { value: VALID_ADDRESS } });
    fireEvent.click(screen.getByRole("button", { name: /add address/i }));

    expect(onChange).toHaveBeenCalledWith([labeled(VALID_ADDRESS)]);
  });

  it("adds a valid SS58 address with a label", () => {
    const onChange = vi.fn();
    render(<AddressManager addresses={[]} onAddressesChange={onChange} />);

    fireEvent.change(screen.getByLabelText(/coldkey address input/i), {
      target: { value: VALID_ADDRESS },
    });
    fireEvent.change(screen.getByLabelText(/address label/i), {
      target: { value: "My Wallet" },
    });
    fireEvent.click(screen.getByRole("button", { name: /add address/i }));

    expect(onChange).toHaveBeenCalledWith([
      labeled(VALID_ADDRESS, "My Wallet"),
    ]);
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
        addresses={[labeled(VALID_ADDRESS)]}
        onAddressesChange={onChange}
      />,
    );

    const input = screen.getByLabelText(/coldkey address input/i);
    fireEvent.change(input, { target: { value: VALID_ADDRESS } });
    fireEvent.click(screen.getByRole("button", { name: /add address/i }));

    expect(onChange).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent(/already added/i);
  });

  it("displays labeled address with label and truncated address", () => {
    render(
      <AddressManager
        addresses={[labeled(VALID_ADDRESS, "Main Wallet")]}
        onAddressesChange={vi.fn()}
      />,
    );
    expect(screen.getByText("Main Wallet")).toBeInTheDocument();
    // Truncated address should be displayed
    expect(
      screen.getByText(`${VALID_ADDRESS.slice(0, 6)}...${VALID_ADDRESS.slice(-6)}`),
    ).toBeInTheDocument();
  });

  it("displays full address when no label is provided", () => {
    render(
      <AddressManager
        addresses={[labeled(VALID_ADDRESS)]}
        onAddressesChange={vi.fn()}
      />,
    );
    expect(screen.getByText(VALID_ADDRESS)).toBeInTheDocument();
  });

  it("shows confirmation before removing an address", () => {
    const onChange = vi.fn();
    render(
      <AddressManager
        addresses={[labeled(VALID_ADDRESS), labeled(VALID_ADDRESS_2)]}
        onAddressesChange={onChange}
      />,
    );

    const removeButtons = screen.getAllByRole("button", {
      name: /remove address/i,
    });
    fireEvent.click(removeButtons[0]);

    // Should show confirmation, not remove yet
    expect(onChange).not.toHaveBeenCalled();
    expect(screen.getByText(/remove\?/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /confirm remove/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /cancel remove/i })).toBeInTheDocument();
  });

  it("removes an address after confirming", () => {
    const onChange = vi.fn();
    render(
      <AddressManager
        addresses={[labeled(VALID_ADDRESS), labeled(VALID_ADDRESS_2)]}
        onAddressesChange={onChange}
      />,
    );

    const removeButtons = screen.getAllByRole("button", {
      name: /remove address/i,
    });
    fireEvent.click(removeButtons[0]);
    fireEvent.click(screen.getByRole("button", { name: /confirm remove/i }));

    expect(onChange).toHaveBeenCalledWith([labeled(VALID_ADDRESS_2)]);
  });

  it("cancels remove when No is clicked", () => {
    const onChange = vi.fn();
    render(
      <AddressManager
        addresses={[labeled(VALID_ADDRESS)]}
        onAddressesChange={onChange}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /remove address/i }));
    fireEvent.click(screen.getByRole("button", { name: /cancel remove/i }));

    expect(onChange).not.toHaveBeenCalled();
    // Confirmation should be dismissed
    expect(screen.queryByText(/remove\?/i)).not.toBeInTheDocument();
  });

  it("adds address on Enter key", () => {
    const onChange = vi.fn();
    render(<AddressManager addresses={[]} onAddressesChange={onChange} />);

    const input = screen.getByLabelText(/coldkey address input/i);
    fireEvent.change(input, { target: { value: VALID_ADDRESS } });
    fireEvent.keyDown(input, { key: "Enter" });

    expect(onChange).toHaveBeenCalledWith([labeled(VALID_ADDRESS)]);
  });

  it("shows error for empty input", () => {
    render(<AddressManager addresses={[]} onAddressesChange={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /add address/i }));
    expect(screen.getByRole("alert")).toHaveTextContent(
      /please enter a coldkey/i,
    );
  });

  it("clears address and label inputs after successful add", () => {
    render(<AddressManager addresses={[]} onAddressesChange={vi.fn()} />);

    const addressInput = screen.getByLabelText(
      /coldkey address input/i,
    ) as HTMLInputElement;
    const labelInput = screen.getByLabelText(
      /address label/i,
    ) as HTMLInputElement;

    fireEvent.change(addressInput, { target: { value: VALID_ADDRESS } });
    fireEvent.change(labelInput, { target: { value: "Test" } });
    fireEvent.click(screen.getByRole("button", { name: /add address/i }));

    expect(addressInput.value).toBe("");
    expect(labelInput.value).toBe("");
  });

  it("shows edit button for each address", () => {
    render(
      <AddressManager
        addresses={[labeled(VALID_ADDRESS, "Wallet A")]}
        onAddressesChange={vi.fn()}
      />,
    );
    expect(
      screen.getByRole("button", { name: /edit label/i }),
    ).toBeInTheDocument();
  });

  it("enters inline edit mode on edit click", () => {
    render(
      <AddressManager
        addresses={[labeled(VALID_ADDRESS, "Old Label")]}
        onAddressesChange={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /edit label/i }));

    const editInput = screen.getByLabelText(/edit address label/i);
    expect(editInput).toBeInTheDocument();
    expect((editInput as HTMLInputElement).value).toBe("Old Label");
  });

  it("saves edited label on Enter", () => {
    const onChange = vi.fn();
    render(
      <AddressManager
        addresses={[labeled(VALID_ADDRESS, "Old")]}
        onAddressesChange={onChange}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /edit label/i }));

    const editInput = screen.getByLabelText(/edit address label/i);
    fireEvent.change(editInput, { target: { value: "New Label" } });
    fireEvent.keyDown(editInput, { key: "Enter" });

    expect(onChange).toHaveBeenCalledWith([
      labeled(VALID_ADDRESS, "New Label"),
    ]);
  });

  it("cancels edit on Escape", () => {
    const onChange = vi.fn();
    render(
      <AddressManager
        addresses={[labeled(VALID_ADDRESS, "Keep This")]}
        onAddressesChange={onChange}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /edit label/i }));

    const editInput = screen.getByLabelText(/edit address label/i);
    fireEvent.change(editInput, { target: { value: "Changed" } });
    fireEvent.keyDown(editInput, { key: "Escape" });

    // onChange should NOT have been called (edit cancelled)
    expect(onChange).not.toHaveBeenCalled();
    // Should exit edit mode — "Keep This" label visible again
    expect(screen.getByText("Keep This")).toBeInTheDocument();
  });

  it("saves edited label on save button click", () => {
    const onChange = vi.fn();
    render(
      <AddressManager
        addresses={[labeled(VALID_ADDRESS, "Old")]}
        onAddressesChange={onChange}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /edit label/i }));
    const editInput = screen.getByLabelText(/edit address label/i);
    fireEvent.change(editInput, { target: { value: "Updated" } });
    fireEvent.click(screen.getByRole("button", { name: /save label/i }));

    expect(onChange).toHaveBeenCalledWith([
      labeled(VALID_ADDRESS, "Updated"),
    ]);
  });
});
