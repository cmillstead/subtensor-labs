import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock next-auth/react
const mockSignIn = vi.fn();
vi.mock("next-auth/react", () => ({
  signIn: (...args: unknown[]) => mockSignIn(...args),
  SessionProvider: ({ children }: { children: React.ReactNode }) => children,
}));

// Mock next/navigation
const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

import LoginPage from "./page";

describe("LoginPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders login form with email, password inputs, and submit button", () => {
    render(<LoginPage />);
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /sign in/i })
    ).toBeInTheDocument();
  });

  it("shows error on invalid credentials", async () => {
    mockSignIn.mockResolvedValue({ error: "CredentialsSignin" });
    const user = userEvent.setup();

    render(<LoginPage />);
    await user.type(screen.getByLabelText(/email/i), "test@example.com");
    await user.type(screen.getByLabelText(/password/i), "wrongpass");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(
      await screen.findByText("Invalid email or password")
    ).toBeInTheDocument();
  });

  it("redirects to dashboard on success", async () => {
    mockSignIn.mockResolvedValue({ error: null });
    const user = userEvent.setup();

    render(<LoginPage />);
    await user.type(screen.getByLabelText(/email/i), "test@example.com");
    await user.type(screen.getByLabelText(/password/i), "correctpass");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await vi.waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/dashboard");
    });
  });

  it("has sign up and forgot password links", () => {
    render(<LoginPage />);
    expect(screen.getByRole("link", { name: /sign up/i })).toHaveAttribute(
      "href",
      "/auth/signup"
    );
    expect(
      screen.getByRole("link", { name: /forgot password/i })
    ).toHaveAttribute("href", "/auth/reset-password");
  });

  it("disables button during submission", async () => {
    // Never-resolving promise to keep loading state
    mockSignIn.mockReturnValue(new Promise(() => {}));
    const user = userEvent.setup();

    render(<LoginPage />);
    await user.type(screen.getByLabelText(/email/i), "test@example.com");
    await user.type(screen.getByLabelText(/password/i), "somepass");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await vi.waitFor(() => {
      expect(screen.getByRole("button")).toBeDisabled();
    });
  });
});
