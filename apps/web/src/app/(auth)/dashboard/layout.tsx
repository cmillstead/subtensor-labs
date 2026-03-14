import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Portfolio Dashboard | Subtensor Labs",
};

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
