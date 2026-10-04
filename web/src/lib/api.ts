// Talks to our Python backend. Every call carries the user's Firebase login token,
// which the backend checks before doing anything.
import { auth } from "./firebase";

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "https://mandap-api-871196743492.asia-south1.run.app";

export async function apiGet<T>(path: string): Promise<T> {
  const user = auth.currentUser;
  const token = user ? await user.getIdToken() : null;

  const res = await fetch(`${API_URL}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

export type Me = { uid: string; email: string | null; role: "couple" | "editor" | "admin" };
