import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock next/navigation
const mockSearchParams = new URLSearchParams();
vi.mock("next/navigation", () => ({
  useSearchParams: () => mockSearchParams,
}));

import ResetPasswordConfirmPage from "./page";

function getPasswordInput() {
  return screen.getByLabelText("New password");
}

function getConfirmPasswordInput() {
  return screen.getByLabelText("Confirm new password");
}

describe("ResetPasswordConfirmPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.restoreAllMocks();
    // Default: valid token in URL
    mockSearchParams.delete("token");
    mockSearchParams.set("token", "test-token-123");
  });

  it("renders confirm form with password and confirm password inputs", () => {
    render(<ResetPasswordConfirmPage />);
    expect(getPasswordInput()).toBeInTheDocument();
    expect(getConfirmPasswordInput()).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /reset password/i })
    ).toBeInTheDocument();
  });

  it("shows error for password mismatch", async () => {
    const user = userEvent.setup();

    render(<ResetPasswordConfirmPage />);
    await user.type(getPasswordInput(), "password123");
    await user.type(getConfirmPasswordInput(), "differentpass");
    await user.click(
      screen.getByRole("button", { name: /reset password/i })
    );

    expect(
      await screen.findByText(/passwords do not match/i)
    ).toBeInTheDocument();
  });

  it("shows error for short password", async () => {
    const user = userEvent.setup();

    render(<ResetPasswordConfirmPage />);
    await user.type(getPasswordInput(), "short");
    await user.type(getConfirmPasswordInput(), "short");
    await user.click(
      screen.getByRole("button", { name: /reset password/i })
    );

    expect(
      await screen.findByText(/at least 8 characters/i)
    ).toBeInTheDocument();
  });

  it("shows success with sign in link on 200", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({ message: "Password has been reset successfully." }),
        { status: 200 }
      )
    );
    const user = userEvent.setup();

    render(<ResetPasswordConfirmPage />);
    await user.type(getPasswordInput(), "newpassword123");
    await user.type(getConfirmPasswordInput(), "newpassword123");
    await user.click(
      screen.getByRole("button", { name: /reset password/i })
    );

    expect(
      await screen.findByText(/password reset successfully/i)
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /sign in/i })
    ).toHaveAttribute("href", "/auth/login");
  });

  it("shows error for expired token (400)", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          error: {
            type: "token_expired",
            message:
              "This reset link has expired. Please request a new one.",
            code: 400,
          },
        }),
        { status: 400 }
      )
    );
    const user = userEvent.setup();

    render(<ResetPasswordConfirmPage />);
    await user.type(getPasswordInput(), "newpassword123");
    await user.type(getConfirmPasswordInput(), "newpassword123");
    await user.click(
      screen.getByRole("button", { name: /reset password/i })
    );

    expect(
      await screen.findByText(/expired/i)
    ).toBeInTheDocument();
  });

  it("shows error when no token in URL", () => {
    mockSearchParams.delete("token");

    render(<ResetPasswordConfirmPage />);
    expect(screen.getByText(/invalid reset link/i)).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /request new reset link/i })
    ).toHaveAttribute("href", "/auth/reset-password");
  });
});
