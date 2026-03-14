import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center py-20">
      <h1 className="text-4xl font-bold">404</h1>
      <p className="mt-4 text-text-secondary">Page not found</p>
      <Link
        href="/"
        className="mt-6 text-sm text-primary hover:text-primary-hover transition-colors"
      >
        Return home
      </Link>
    </div>
  );
}
