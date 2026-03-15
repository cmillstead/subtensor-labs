import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Explore Portfolio | Subtensor Labs",
  description:
    "Paste any Bittensor coldkey address to view portfolio positions, subnet allocations, and delegation details. No account required.",
  openGraph: {
    title: "Explore Portfolio | Subtensor Labs",
    description:
      "Paste any Bittensor coldkey address to view portfolio positions, subnet allocations, and delegation details.",
    type: "website",
  },
};

export default function ExploreLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
