/** Allowed engine path prefixes — reject anything outside this list. */
export const ALLOWED_PREFIXES = [
  "/engine/health",
  "/engine/portfolio",
  "/engine/screener",
  "/engine/subnets",
  "/engine/predictions",
  "/engine/alerts",
  "/engine/users",
];

export function isAllowed(path: string): boolean {
  // Normalize to prevent path traversal (e.g., "/engine/health/../admin")
  const normalized = new URL(path, "http://localhost").pathname;
  return ALLOWED_PREFIXES.some((prefix) => normalized.startsWith(prefix));
}
