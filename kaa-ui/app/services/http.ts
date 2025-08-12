export type AppError = { code?: string; message: string; details?: unknown };

export const baseURL = import.meta.env.VITE_API_BASE_URL ?? "";

export async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const url = baseURL + path;
  const resp = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  const contentType = resp.headers.get("content-type") ?? "";
  if (!resp.ok) {
    let message = resp.statusText;
    try {
      if (contentType.includes("application/json")) {
        const body = await resp.json();
        message = body?.message || message;
      } else {
        message = await resp.text();
      }
    } catch {}
    throw { message } satisfies AppError;
  }
  if (contentType.includes("application/json")) return (await resp.json()) as T;
  return (await resp.text()) as unknown as T;
}

export const get = <T>(path: string) => http<T>(path);
export const post = <T>(path: string, body?: unknown) => http<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined });
export const put = <T>(path: string, body?: unknown) => http<T>(path, { method: "PUT", body: body ? JSON.stringify(body) : undefined });
export const patch = <T>(path: string, body?: unknown) => http<T>(path, { method: "PATCH", body: body ? JSON.stringify(body) : undefined });
export const del = <T>(path: string) => http<T>(path, { method: "DELETE" }); 