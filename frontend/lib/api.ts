// Thin client for the Umbra API. Everything goes through the same-origin /api proxy (see next.config.ts).

export type ApiErrorKind = "offline" | "http";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public kind: ApiErrorKind,
  ) {
    super(message);
  }
}

export async function api<T>(path: string, init: RequestInit & { json?: unknown } = {}): Promise<T> {
  const { json, headers, ...rest } = init;
  let res: Response;
  try {
    res = await fetch(`/api${path}`, {
      ...rest,
      headers: { ...(json !== undefined ? { "content-type": "application/json" } : {}), ...headers },
      body: json !== undefined ? JSON.stringify(json) : rest.body,
      cache: "no-store",
    });
  } catch {
    throw new ApiError("Can't reach Umbra. You may be offline.", 0, "offline");
  }
  const type = res.headers.get("content-type") || "";
  if (!res.ok) {
    if (!type.includes("application/json")) {
      // The Next proxy answers 500 with HTML/text when the backend process isn't running.
      throw new ApiError("The Umbra backend isn't responding.", res.status, res.status >= 500 ? "offline" : "http");
    }
    const body = await res.json().catch(() => ({}));
    const detail = typeof body.detail === "string" ? body.detail : `Request failed (${res.status})`;
    throw new ApiError(detail, res.status, "http");
  }
  if (type.includes("application/json")) return (await res.json()) as T;
  return (await res.blob()) as unknown as T;
}

export const post = <T>(path: string, json?: unknown, init: RequestInit = {}) =>
  api<T>(path, { method: "POST", json: json ?? {}, ...init });

/** Wall-clock helpers kept outside components (render must stay pure; these are only called from handlers). */
export const nowMs = () => Date.now();
export const secondsSince = (start: number) => Math.round((Date.now() - start) / 1000);
