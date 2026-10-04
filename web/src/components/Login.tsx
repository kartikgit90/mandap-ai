"use client";

import { useEffect, useState } from "react";
import {
  GoogleAuthProvider,
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  signInAnonymously,
  signInWithPopup,
} from "firebase/auth";
import { auth } from "@/lib/firebase";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  // A link ending in ?demo=1 opens the app straight away as a guest, with no sign-up.
  // Each guest gets their own private demo wedding.
  useEffect(() => {
    if (new URLSearchParams(window.location.search).get("demo") === "1") run(() => signInAnonymously(auth));
  }, []);

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
    <main className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <h1 className="font-serif text-5xl font-bold">Mandap AI</h1>
        <p className="mt-2 text-muted">Find your look for every function, and plan your destination wedding.</p>

        <div className="card mt-8 p-6">
          <button onClick={() => run(() => signInAnonymously(auth))} disabled={busy} className="btn-primary w-full py-3">
            {busy ? "Opening…" : "Explore the demo"}
          </button>
          <p className="mt-2 text-center text-xs text-soft">No sign-up needed</p>
          <button
            onClick={() => run(() => signInWithPopup(auth, new GoogleAuthProvider()))}
            disabled={busy}
            className="btn-ghost mt-4 w-full py-3"
          >
            Continue with Google
          </button>
          <div className="my-5 flex items-center gap-3 text-xs text-soft">
            <span className="h-px flex-1 bg-line" /> or <span className="h-px flex-1 bg-line" />
          </div>
          <label className="sr-only" htmlFor="email">Email</label>
          <input id="email" type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-lg border border-line-strong px-3 py-2.5 text-sm outline-none focus:border-brand" />
          <label className="sr-only" htmlFor="password">Password</label>
          <input id="password" type="password" placeholder="Password (6+ characters)" value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-2 w-full rounded-lg border border-line-strong px-3 py-2.5 text-sm outline-none focus:border-brand" />
          <div className="mt-3 flex gap-2">
            <button onClick={() => run(() => signInWithEmailAndPassword(auth, email, password))} disabled={busy} className="btn-ghost flex-1">Log in</button>
            <button onClick={() => run(() => createUserWithEmailAndPassword(auth, email, password))} disabled={busy} className="btn-ghost flex-1">Sign up</button>
          </div>
          {error && <p className="mt-4 text-sm text-red-700">{error}</p>}
        </div>
        <p className="mt-4 text-xs text-soft">Prototype. Brands, products and prices are demo data.</p>
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
    "auth/admin-restricted-operation": "Guest access isn't switched on yet. Please use Google for now.",
    "auth/unauthorized-domain": "This website address isn't allowed in Firebase yet.",
  };
  return map[code] ?? (e as Error)?.message ?? "Something went wrong.";
}
