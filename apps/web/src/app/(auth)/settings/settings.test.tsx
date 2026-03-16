import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import SettingsPage from "./page";

// Mock TanStack Query
vi.mock("@tanstack/react-query", async () => {
  const actual = await vi.importActual("@tanstack/react-query");
  return {
    ...actual,
    useQuery: vi.fn().mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    }),
    useMutation: vi.fn().mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    }),
  };
});

// Mock next-auth/react
vi.mock("next-auth/react", () => ({
  useSession: vi.fn().mockReturnValue({
    data: null,
    status: "unauthenticated",
  }),
  SessionProvider: ({ children }: { children: React.ReactNode }) => children,
}));

// Mock query client
vi.mock("@/lib/query-client", () => ({
  getQueryClient: vi.fn().mockReturnValue({
    mount: vi.fn(),
    unmount: vi.fn(),
    getQueryCache: vi.fn().mockReturnValue({ subscribe: vi.fn(() => vi.fn()) }),
    getMutationCache: vi.fn().mockReturnValue({ subscribe: vi.fn(() => vi.fn()) }),
    getDefaultOptions: vi.fn().mockReturnValue({}),
    setDefaultOptions: vi.fn(),
    isFetching: vi.fn(),
    isMutating: vi.fn(),
  }),
}));

describe("SettingsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders page title and description", () => {
    render(<SettingsPage />);
    expect(screen.getByRole("heading", { level: 1, name: /settings/i })).toBeInTheDocument();
    expect(screen.getByText(/manage your saved addresses/i)).toBeInTheDocument();
  });

  it("renders Saved Addresses section", () => {
    render(<SettingsPage />);
    expect(screen.getByRole("heading", { level: 2, name: /saved addresses/i })).toBeInTheDocument();
  });

  it("renders address input field", () => {
    render(<SettingsPage />);
    expect(screen.getByLabelText(/coldkey address input/i)).toBeInTheDocument();
  });

  it("renders Add Address button", () => {
    render(<SettingsPage />);
    expect(screen.getByRole("button", { name: /add address/i })).toBeInTheDocument();
  });
});
