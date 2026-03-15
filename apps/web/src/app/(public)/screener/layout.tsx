import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Subnet Screener | Subtensor Labs",
  description:
    "Browse and compare all Bittensor subnets. Sort by emission share, miner count, alpha price, and more.",
  openGraph: {
    title: "Subnet Screener | Subtensor Labs",
    description:
      "Browse and compare all Bittensor subnets. Sort by emission share, miner count, alpha price, and more.",
    type: "website",
  },
};

export default function ScreenerLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
