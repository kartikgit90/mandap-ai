"use client";

// First page: log in, then ask the backend "who am I?".
// If this shows your email and role, the whole chain works:
// website -> Firebase login -> our backend -> role check.

import { useEffect, useState } from "react";
import {
  GoogleAuthProvider,
  createUserWithEmailAndPassword,
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signInWithPopup,
  signOut,
  type User,
} from "firebase/auth";
import { auth } from "@/lib/firebase";
import { apiGet, apiPost, type LlmTest, type Me } from "@/lib/api";

export default function Home() {
  const [user, setUser] = useState<User | null>(null);
  const [me, setMe] = useState<Me | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [llmTest, setLlmTest] = useState<LlmTest | null>(null);

  useEffect(() => onAuthStateChanged(auth, setUser), []);

  // Once logged in, ask the backend who we are.
  useEffect(() => {
    if (!user) {
      setMe(null);
      return;
    }
    apiGet<Me>("/me")
      .then(setMe)
      .catch((e: Error) => setError(`Backend: ${e.message}`));
  }, [user]);

  async function run(action: () => Promise<unknown>) {
    setError("");
    setBusy(true);
    try {
      await action();
    } catch (e) {
      setError(friendly(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="min-h-screen flex items-center justify-center bg-[#faf6f0] px-4 text-[#2b1d14]">
      <div className="w-full max-w-sm">
        <h1 className="font-serif text-4xl tracking-tight">Mandap AI</h1>
        <p className="mt-2 text-sm text-[#6b5444]">Plan your wedding, one function at a time.</p>

        <div className="mt-8 rounded-2xl border border-[#e8dccd] bg-white p-6 shadow-sm">
          {!user ? (
            <>
              <button
                onClick={() => run(() => signInWithPopup(auth, new GoogleAuthProvider()))}
                disabled={busy}
                className="w-full rounded-lg bg-[#7a1f2b] px-4 py-2.5 text-sm font-medium text-white hover:bg-[#651922] disabled:opacity-60"
              >
                Continue with Google
              </button>

              <div className="my-5 flex items-center gap-3 text-xs text-[#9a8574]">
                <span className="h-px flex-1 bg-[#e8dccd]" /> or <span className="h-px flex-1 bg-[#e8dccd]" />
              </div>

              <input
                type="email"
                placeholder="Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-lg border border-[#e8dccd] px-3 py-2 text-sm outline-none focus:border-[#7a1f2b]"
              />
              <input
                type="password"
                placeholder="Password (6+ characters)"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-2 w-full rounded-lg border border-[#e8dccd] px-3 py-2 text-sm outline-none focus:border-[#7a1f2b]"
              />
              <div className="mt-3 flex gap-2">
                <button
                  onClick={() => run(() => signInWithEmailAndPassword(auth, email, password))}
                  disabled={busy}
                  className="flex-1 rounded-lg border border-[#7a1f2b] px-3 py-2 text-sm text-[#7a1f2b] hover:bg-[#fbf1f2] disabled:opacity-60"
                >
                  Log in
                </button>
                <button
                  onClick={() => run(() => createUserWithEmailAndPassword(auth, email, password))}
                  disabled={busy}
                  className="flex-1 rounded-lg border border-[#e8dccd] px-3 py-2 text-sm hover:bg-[#faf6f0] disabled:opacity-60"
                >
                  Sign up
                </button>
              </div>
            </>
          ) : (
            <>
              <p className="text-sm text-[#6b5444]">Logged in as</p>
              <p className="font-medium">{user.email}</p>

              <div className="mt-4 rounded-lg bg-[#faf6f0] p-3 text-sm">
                {me ? (
                  <>
                    <p>
                      Backend says your role is <b>{me.role}</b>
                    </p>
                    <p className="mt-1 break-all text-xs text-[#9a8574]">User id: {me.uid}</p>
                  </>
                ) : (
                  !error && <p>Checking with the backend...</p>
                )}
              </div>

              {me?.role === "admin" && (
                <div className="mt-4 rounded-lg border border-[#e8dccd] p-3 text-sm">
                  <p className="font-medium">Admin: test Claude</p>
                  <button
                    onClick={() => run(async () => setLlmTest(await apiPost<LlmTest>("/admin/llm-test")))}
                    disabled={busy}
                    className="mt-2 w-full rounded-lg bg-[#7a1f2b] px-3 py-2 text-sm text-white hover:bg-[#651922] disabled:opacity-60"
                  >
                    {busy ? "Asking Claude..." : "Test Claude"}
                  </button>
                  {llmTest && (
                    <div className="mt-3 space-y-1">
                      <p>&ldquo;{llmTest.reply}&rdquo;</p>
                      <p className="text-xs text-[#9a8574]">
                        {llmTest.model} via {llmTest.provider} · {llmTest.tokens_in} in / {llmTest.tokens_out} out
                        tokens · ₹{llmTest.cost_inr.toFixed(4)} · {(llmTest.latency_ms / 1000).toFixed(1)}s
                      </p>
                    </div>
                  )}
                </div>
              )}

              <button
                onClick={() => run(() => signOut(auth))}
                className="mt-4 w-full rounded-lg border border-[#e8dccd] px-3 py-2 text-sm hover:bg-[#faf6f0]"
              >
                Log out
              </button>
            </>
          )}

          {error && <p className="mt-4 text-sm text-[#b42318]">{error}</p>}
        </div>
      </div>
    </main>
  );
}

function friendly(e: unknown): string {
  const code = (e as { code?: string })?.code ?? "";
  const map: Record<string, string> = {
    "auth/invalid-credential": "Wrong email or password.",
    "auth/email-already-in-use": "That email already has an account. Try Log in.",
    "auth/weak-password": "Password must be at least 6 characters.",
    "auth/invalid-email": "That doesn't look like an email address.",
    "auth/popup-closed-by-user": "Login window was closed.",
    "auth/unauthorized-domain": "This website address isn't allowed in Firebase yet.",
  };
  return map[code] ?? (e as Error)?.message ?? "Something went wrong.";
}
