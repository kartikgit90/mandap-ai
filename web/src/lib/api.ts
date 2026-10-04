// Talks to our Python backend. Every call carries the user's Firebase login token,
// which the backend checks before doing anything.
import { auth } from "./firebase";

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "https://mandap-api-871196743492.asia-south1.run.app";

export function apiGet<T>(path: string): Promise<T> {
  return request<T>("GET", path);
}

export function apiPost<T>(path: string, body?: unknown): Promise<T> {
  return request<T>("POST", path, body);
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const user = auth.currentUser;
  const token = user ? await user.getIdToken() : null;

  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";

  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

export type Me = { uid: string; email: string | null; role: "couple" | "editor" | "admin" };

export type LlmTest = {
  reply: string;
  model: string;
  provider: string;
  tokens_in: number;
  tokens_out: number;
  cost_inr: number;
  latency_ms: number;
};
