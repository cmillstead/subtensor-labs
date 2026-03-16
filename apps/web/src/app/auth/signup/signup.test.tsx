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

// Mock fetch
const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

import SignupPage from "./page";

describe("SignupPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders signup form with email, password, and confirm password inputs", () => {
    render(<SignupPage />);
    expect(screen.getByLabelText(/^email$/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /create account/i })
    ).toBeInTheDocument();
  });

  it("shows validation error for mismatched passwords", async () => {
    const user = userEvent.setup();

    render(<SignupPage />);
    await user.type(screen.getByLabelText(/^email$/i), "test@example.com");
    await user.type(screen.getByLabelText(/^password$/i), "securepass123");
    await user.type(screen.getByLabelText(/confirm password/i), "different123");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    expect(
      await screen.findByText("Passwords do not match")
    ).toBeInTheDocument();
    // Should not call fetch since validation failed
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it("shows validation error for short password", async () => {
    const user = userEvent.setup();

    render(<SignupPage />);
    await user.type(screen.getByLabelText(/^email$/i), "test@example.com");
    await user.type(screen.getByLabelText(/^password$/i), "short");
    await user.type(screen.getByLabelText(/confirm password/i), "short");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    expect(
      await screen.findByText("Password must be at least 8 characters")
    ).toBeInTheDocument();
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it("shows error for duplicate email", async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 409,
      json: async () => ({
        error: { type: "duplicate_email", message: "Email already exists", code: 409 },
      }),
    });
    const user = userEvent.setup();

    render(<SignupPage />);
    await user.type(screen.getByLabelText(/^email$/i), "existing@example.com");
    await user.type(screen.getByLabelText(/^password$/i), "securepass123");
    await user.type(
      screen.getByLabelText(/confirm password/i),
      "securepass123"
    );
    await user.click(screen.getByRole("button", { name: /create account/i }));

    expect(
      await screen.findByText("An account with this email already exists")
    ).toBeInTheDocument();
  });

  it("completes successful signup flow", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ data: { id: 1, email: "new@example.com" } }),
    });
    mockSignIn.mockResolvedValue({ error: null });
    const user = userEvent.setup();

    render(<SignupPage />);
    await user.type(screen.getByLabelText(/^email$/i), "new@example.com");
    await user.type(screen.getByLabelText(/^password$/i), "securepass123");
    await user.type(
      screen.getByLabelText(/confirm password/i),
      "securepass123"
    );
    await user.click(screen.getByRole("button", { name: /create account/i }));

    await vi.waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        "/api/proxy/engine/users/register",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            email: "new@example.com",
            password: "securepass123",
          }),
        })
      );
      expect(mockSignIn).toHaveBeenCalledWith("credentials", {
        email: "new@example.com",
        password: "securepass123",
        redirect: false,
      });
      expect(mockPush).toHaveBeenCalledWith("/dashboard");
    });
  });

  it("has sign in link", () => {
    render(<SignupPage />);
    expect(screen.getByRole("link", { name: /sign in/i })).toHaveAttribute(
      "href",
      "/auth/login"
    );
  });
});
