import { ENGINE_URL } from "./constants";

export class EngineClientError extends Error {
  readonly type: string;
  readonly statusCode: number;

  constructor(type: string, message: string, statusCode: number) {
    super(message);
    Object.setPrototypeOf(this, new.target.prototype);
    this.name = "EngineClientError";
    this.type = type;
    this.statusCode = statusCode;
  }
}

/**
 * Typed HTTP client for the Python engine.
 *
 * Intended for use in Next.js Server Components and server-side code that
 * needs direct engine access. Browser clients should use the `/api/proxy/`
 * route instead, which enforces the path allowlist and handles CORS.
 */
export async function engineFetch<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const url = `${ENGINE_URL}/engine${path}`;

  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    });
  } catch (err) {
    throw new EngineClientError(
      "network_error",
      `Failed to reach engine: ${err instanceof Error ? err.message : String(err)}`,
      0,
    );
  }

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const errorType = body?.error?.type ?? "engine_error";
    const errorMessage =
      body?.error?.message ?? `Engine returned ${response.status}`;
    throw new EngineClientError(errorType, errorMessage, response.status);
  }

  try {
    return await response.json();
  } catch {
    throw new EngineClientError(
      "parse_error",
      "Invalid JSON in engine response",
      response.status,
    );
  }
}
