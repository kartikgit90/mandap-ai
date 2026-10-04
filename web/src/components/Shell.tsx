"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { signOut } from "firebase/auth";
import type { ReactNode } from "react";
import { auth } from "@/lib/firebase";
import { useAuth } from "@/lib/auth";
import Login from "./Login";

const LIVE = [
  { href: "/shop-the-look", label: "Shop the Look", icon: <path d="M8 3l3 3 3-3 4 3-2 4h-2v9H8v-9H6L4 6z" /> },
  { href: "/destinations", label: "Destination weddings", icon: <><path d="M11 19s6-5.5 6-10a6 6 0 00-12 0c0 4.5 6 10 6 10z" /><circle cx="11" cy="9" r="2" /></> },
];

// Behind the scenes: what the AI is allowed to know.
const MAGAZINE = [
  { href: "/knowledge", label: "Knowledge base", icon: <><path d="M4 4h6a2 2 0 012 2v12a2 2 0 00-2-2H4z" /><path d="M18 4h-6a2 2 0 00-2 2v12a2 2 0 012-2h6z" /></> },
];

export const SOON = [
  { label: "Vendors", note: "Photographers, decorators, caterers" },
  { label: "Budget", note: "Split across every function" },
  { label: "Checklist", note: "Tasks and timeline" },
  { label: "Astrology & muhurat", note: "Auspicious dates" },
  { label: "Honeymoon", note: "Destinations and packages" },
  { label: "Beauty & grooming", note: "Artists and prep plans" },
  { label: "Home & gifting", note: "Return gifts and trousseau" },
];

export default function Shell({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const path = usePathname();

  if (loading) return <div className="min-h-screen" />;
  if (!user) return <Login />;

  const item = (active: boolean) =>
    `flex items-center gap-2.5 rounded-[10px] px-3 py-2.5 text-sm no-underline ${
      active ? "bg-blush text-brand font-bold" : "text-ink font-semibold hover:bg-cream"
    }`;

  return (
    <div className="min-h-screen flex flex-wrap">
      <aside className="flex-[1_1_248px] max-w-[272px] bg-white border-r border-line px-3.5 py-5 flex flex-col gap-0.5">
        <Link href="/" className="flex items-center gap-2.5 px-2.5 pb-5 no-underline text-ink">
          <svg width="26" height="26" viewBox="0 0 28 28" fill="none" stroke="#C45A1C" strokeWidth="1.6" aria-hidden><path d="M4 24V12l10-8 10 8v12" /><path d="M9 24v-7h10v7" /><path d="M14 4v-2" /></svg>
          <span className="font-serif text-[23px] font-bold text-brand">Wedding Affair</span>
        </Link>
        <Link href="/" className={item(path === "/")}>
          <svg width="18" height="18" viewBox="0 0 22 22" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden><path d="M3 10l8-6 8 6v9H3z" /></svg>Home
        </Link>

        <p className="mt-4 mb-1.5 px-3 text-[11px] font-bold uppercase tracking-[1.2px] text-soft">Live</p>
        {LIVE.map((l) => (
          <Link key={l.href} href={l.href} className={item(path.startsWith(l.href))}>
            <svg width="18" height="18" viewBox="0 0 22 22" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden>{l.icon}</svg>
            {l.label}
          </Link>
        ))}

        <p className="mt-4 mb-1.5 px-3 text-[11px] font-bold uppercase tracking-[1.2px] text-soft">For the magazine team</p>
        {MAGAZINE.map((l) => (
          <Link key={l.href} href={l.href} className={item(path.startsWith(l.href))}>
            <svg width="18" height="18" viewBox="0 0 22 22" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden>{l.icon}</svg>
            {l.label}
          </Link>
        ))}

        <p className="mt-4 mb-1.5 px-3 text-[11px] font-bold uppercase tracking-[1.2px] text-soft">Coming soon</p>
        {SOON.map((s) => (
          <span key={s.label} className="flex items-center gap-2.5 rounded-[10px] px-3 py-2 text-sm text-soft">
            {s.label}
            <span className="ml-auto rounded-md border border-line-strong px-1.5 py-0.5 text-[10px] font-bold tracking-wide">SOON</span>
          </span>
        ))}

        <div className="mt-auto pt-4 border-t border-line flex items-center gap-2.5 px-3">
          <span className="w-9 h-9 rounded-full bg-blush flex items-center justify-center text-[13px] font-bold">
            {(user.displayName ?? user.email ?? "Guest").slice(0, 1).toUpperCase()}
          </span>
          <span className="flex-1 min-w-0 text-[13px]">
            <span className="block font-bold truncate">{user.displayName ?? user.email ?? "Guest"}</span>
            <button onClick={() => signOut(auth)} className="text-soft hover:text-brand">Log out</button>
          </span>
        </div>
      </aside>

      <main className="flex-[999_1_560px] min-w-0 px-5 py-7 md:px-8">
        {children}
        <p className="mt-10 text-xs text-soft">Prototype for Wedding Affair. Brands, products and prices are demo data.</p>
      </main>
    </div>
  );
}
