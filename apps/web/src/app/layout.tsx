import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Subtensor Labs — Bittensor Portfolio, Predictions & Subnet Screener",
  description:
    "Unified portfolio tracking, predictive analytics, and multi-criteria subnet screening for the Bittensor network.",
  openGraph: {
    title: "Subtensor Labs",
    description:
      "Unified portfolio tracking, predictive analytics, and multi-criteria subnet screening for the Bittensor network.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${inter.variable} ${jetbrainsMono.variable} antialiased`}
      >
        <a href="#main" className="skip-link">
          Skip to main content
        </a>
        <TickerBar />
        <Navigation />
        <main id="main" tabIndex={-1} className="mx-auto max-w-[1440px] px-6 py-6 outline-none">
          {children}
        </main>
      </body>
    </html>
  );
}

function TickerBar() {
  return (
    <div
      role="status"
      aria-live="polite"
      className="flex h-9 items-center justify-center gap-6 bg-surface text-xs"
    >
      <span className="text-text-secondary">
        TAO Price: <span aria-label="Loading">—</span>
      </span>
      <span className="text-text-secondary">
        MCap: <span aria-label="Loading">—</span>
      </span>
      <span className="text-text-secondary">
        Block: <span aria-label="Loading">—</span>
      </span>
    </div>
  );
}

function Navigation() {
  return (
    <nav
      aria-label="Main navigation"
      className="flex h-14 items-center justify-between border-b border-border bg-background px-6"
    >
      <Link href="/" className="text-lg font-semibold text-text-primary">
        Subtensor Labs
      </Link>
      <ul className="flex list-none gap-6 text-sm">
        <li>
          <Link
            href="/screener"
            className="text-text-secondary hover:text-text-primary transition-colors"
          >
            Screener
          </Link>
        </li>
        <li>
          <Link
            href="/dashboard"
            className="text-text-secondary hover:text-text-primary transition-colors"
          >
            Portfolio
          </Link>
        </li>
        <li>
          <Link
            href="/predictions"
            className="text-text-secondary hover:text-text-primary transition-colors"
          >
            Predictions
          </Link>
        </li>
        <li>
          <Link
            href="/alerts"
            className="text-text-secondary hover:text-text-primary transition-colors"
          >
            Alerts
          </Link>
        </li>
      </ul>
      <Link
        href="/auth/login"
        className="text-sm text-text-muted hover:text-text-primary transition-colors"
      >
        Sign In
      </Link>
    </nav>
  );
}
