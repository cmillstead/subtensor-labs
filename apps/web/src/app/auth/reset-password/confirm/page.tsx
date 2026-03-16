"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";

function ResetPasswordConfirmForm() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  if (!token) {
    return (
      <div className="w-full max-w-[480px] rounded-lg border border-border bg-surface p-8">
        <h1 className="mb-4 text-2xl font-semibold text-text-primary">
          Invalid reset link
        </h1>
        <p className="mb-6 text-sm text-text-secondary">
          This password reset link is invalid. Please request a new one.
        </p>
        <Link
          href="/auth/reset-password"
          className="text-sm text-accent hover:underline"
        >
          Request new reset link
        </Link>
      </div>
    );
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setIsLoading(true);

    try {
      const res = await fetch(
        "/api/proxy/engine/users/reset-password/confirm",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token, password }),
        }
      );

      if (res.ok) {
        setIsSuccess(true);
      } else {
        const data = await res.json();
        setError(
          data?.error?.message ||
            "An unexpected error occurred. Please try again."
        );
      }
    } catch {
      setError("An unexpected error occurred. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }

  if (isSuccess) {
    return (
      <div className="w-full max-w-[480px] rounded-lg border border-border bg-surface p-8">
        <h1 className="mb-4 text-2xl font-semibold text-text-primary">
          Password reset successfully
        </h1>
        <p className="mb-6 text-sm text-text-secondary">
          Your password has been updated. You can now sign in with your new
          password.
        </p>
        <Link
          href="/auth/login"
          className="text-sm text-accent hover:underline"
        >
          Sign in
        </Link>
      </div>
    );
  }

  return (
    <div className="w-full max-w-[480px] rounded-lg border border-border bg-surface p-8">
      <h1 className="mb-2 text-2xl font-semibold text-text-primary">
        Set new password
      </h1>
      <p className="mb-6 text-sm text-text-secondary">
        Enter your new password below.
      </p>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label
            htmlFor="password"
            className="mb-1.5 block text-sm text-text-secondary"
          >
            New password
          </label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="new-password"
            className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-accent"
            placeholder="Min. 8 characters"
          />
        </div>

        <div>
          <label
            htmlFor="confirm-password"
            className="mb-1.5 block text-sm text-text-secondary"
          >
            Confirm new password
          </label>
          <input
            id="confirm-password"
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
            autoComplete="new-password"
            className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-accent"
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
            <Loader2 className="animate-spin" aria-label="Resetting password" />
          ) : (
            "Reset password"
          )}
        </Button>
      </form>

      <div className="mt-6 text-center text-sm">
        <Link
          href="/auth/reset-password"
          className="text-text-muted hover:text-text-secondary"
        >
          Request new reset link
        </Link>
      </div>
    </div>
  );
}

export default function ResetPasswordConfirmPage() {
  return (
    <div className="flex min-h-[calc(100vh-128px)] items-center justify-center">
      <Suspense>
        <ResetPasswordConfirmForm />
      </Suspense>
    </div>
  );
}
