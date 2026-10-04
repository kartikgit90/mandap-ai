// Talks to our Python backend. Every call carries the user's Firebase login token,
// which the backend checks before doing anything.
import { auth } from "./firebase";

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "https://mandap-api-871196743492.asia-south1.run.app";

export const api = {
  get: <T,>(path: string) => request<T>("GET", path),
  post: <T,>(path: string, body?: unknown) => request<T>("POST", path, body),
  put: <T,>(path: string, body?: unknown) => request<T>("PUT", path, body),
  del: <T,>(path: string) => request<T>("DELETE", path),
};

// Kept for older code
export const apiGet = api.get;
export const apiPost = api.post;

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
    const data = await res.json().catch(() => ({}));
    const detail = typeof data.detail === "string" ? data.detail : `Request failed (${res.status})`;
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

// ---------- Types shared with the backend ----------

export type Me = { uid: string; email: string | null; role: "couple" | "editor" | "admin" };

export type Wedding = {
  couple: string;
  date: string;
  guests: number;
  days: number;
  budget: number;
  functions: string[];
};

export type Source = { tier: "verified" | "published"; title: string };

export type Piece = {
  id: string;
  name: string;
  brand: string;
  kind: string;
  price: number;
  colors: string[];
  lead_time_weeks?: number;
  seen_in?: { id: string; title: string; issue: string } | null;
  image?: string | null;
  image_credit?: string | null;
};

export type Look = {
  id: string;
  title: string;
  function: string;
  side: string;
  why: string;
  top_pick?: boolean;
  total: number;
  within_budget?: boolean;
  pieces: Piece[];
};

export type Enquiry = {
  id: string;
  status: "draft" | "sent";
  brand: string;
  items: { id: string; name: string; price: number }[];
  questions: string[];
  shares: string[];
  never_shares: string[];
  created_at: string;
  sent_at?: string;
};

export type EstimateLine = { key: string; label: string; amount: number };
export type Estimate = {
  destination: string;
  name: string;
  guests: number;
  days: number;
  lines: EstimateLine[];
  total: number;
  range: [number, number];
  overrides: Record<string, number>;
  source: { tier: string; title: string; valid_until: string };
};

export type DestinationCard = {
  id: string;
  name: string;
  vibe: string;
  travel: string;
  weather: string;
  month: string;
  estimate: Estimate;
  over_budget: boolean;
};

export type Proposal = {
  destination: string;
  name: string;
  summary: string;
  overrides: Record<string, number>;
  before_total: number;
  after_total: number;
};

export type Plan = {
  wedding: Wedding;
  destination: string;
  overrides: Record<string, number>;
  shortlist: DestinationCard[];
  estimate: Estimate;
};

export type AgentEvents = {
  looks: Look[];
  drafts: Enquiry[];
  proposals: Proposal[];
  shortlist: DestinationCard[];
  estimates: Estimate[];
  sources: Source[];
};

export type AgentReply = {
  reply: string;
  events: AgentEvents;
  usage: { model: string; tokens_in: number; tokens_out: number; cost_inr: number; tools: string[] };
};

export type ChatMsg = { role: "user" | "assistant"; content: string };

// ---------- Formatting ----------

/** ₹ in Indian style: 4500000 -> ₹45 L, 55000 -> ₹55K */
export function inr(n: number): string {
  if (n >= 100000) {
    const v = n / 100000;
    return `₹${v.toFixed(v >= 10 ? 1 : 2).replace(/\.0+$/, "").replace(/(\.\d)0$/, "$1")} L`;
  }
  return `₹${Math.round(n / 1000)}K`;
}
