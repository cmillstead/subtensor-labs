"use client";

import { useState } from "react";
import Link from "next/link";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function ResetPasswordPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      const res = await fetch("/api/proxy/engine/users/reset-password/request", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });

      if (!res.ok) {
        setError("An unexpected error occurred. Please try again.");
      } else {
        setIsSubmitted(true);
      }
    } catch {
      setError("An unexpected error occurred. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }

  if (isSubmitted) {
    return (
      <div className="flex min-h-[calc(100vh-128px)] items-center justify-center">
        <div className="w-full max-w-[480px] rounded-lg border border-border bg-surface p-8">
          <h1 className="mb-4 text-2xl font-semibold text-text-primary">
            Check your email
          </h1>
          <p className="mb-6 text-sm text-text-secondary">
            If an account exists with this email, a reset link has been sent.
            Check your inbox.
          </p>
          <Link
            href="/auth/login"
            className="text-sm text-accent hover:underline"
          >
            Back to sign in
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-[calc(100vh-128px)] items-center justify-center">
      <div className="w-full max-w-[480px] rounded-lg border border-border bg-surface p-8">
        <h1 className="mb-2 text-2xl font-semibold text-text-primary">
          Reset your password
        </h1>
        <p className="mb-6 text-sm text-text-secondary">
          Enter your email address and we&apos;ll send you a link to reset your
          password.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="email"
              className="mb-1.5 block text-sm text-text-secondary"
            >
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-accent"
              placeholder="you@example.com"
            />
          </div>

          {error && (
            <p role="alert" className="text-sm text-rose-400">
              {error}
            </p>
          )}

          <Button
            type="submit"
            disabled={isLoading}
            className="w-full"
          >
            {isLoading ? (
              <Loader2 className="animate-spin" aria-label="Sending reset link" />
            ) : (
              "Send reset link"
            )}
          </Button>
        </form>

        <div className="mt-6 text-center text-sm">
          <Link
            href="/auth/login"
            className="text-text-muted hover:text-text-secondary"
          >
            Back to sign in
          </Link>
        </div>
      </div>
    </div>
  );
}
