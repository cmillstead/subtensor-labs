import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";

import ResetPasswordPage from "./page";

describe("ResetPasswordPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  it("renders request form with email input and submit button", () => {
    render(<ResetPasswordPage />);
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /send reset link/i })
    ).toBeInTheDocument();
  });

  it("shows success message after submission", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ message: "ok" }), { status: 200 })
    );
    const user = userEvent.setup();

    render(<ResetPasswordPage />);
    await user.type(screen.getByLabelText(/email/i), "test@example.com");
    await user.click(
      screen.getByRole("button", { name: /send reset link/i })
    );

    expect(
      await screen.findByText(/check your email/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/reset link has been sent/i)
    ).toBeInTheDocument();
  });

  it("has back to sign in link", () => {
    render(<ResetPasswordPage />);
    expect(
      screen.getByRole("link", { name: /back to sign in/i })
    ).toHaveAttribute("href", "/auth/login");
  });

  it("disables button during submission", async () => {
    vi.spyOn(global, "fetch").mockReturnValue(new Promise(() => {}));
    const user = userEvent.setup();

    render(<ResetPasswordPage />);
    await user.type(screen.getByLabelText(/email/i), "test@example.com");
    await user.click(
      screen.getByRole("button", { name: /send reset link/i })
    );

    await vi.waitFor(() => {
      expect(screen.getByRole("button")).toBeDisabled();
    });
  });
});
