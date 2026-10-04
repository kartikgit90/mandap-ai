"use client";

import { useEffect, useState } from "react";
import ChatPanel from "@/components/ChatPanel";
import Shell from "@/components/Shell";
import { api, inr, type AgentReply, type DestinationCard, type Plan, type Proposal } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function Destinations() {
  return (
    <Shell>
      <Body />
    </Shell>
  );
}

function Body() {
  const { user } = useAuth();
  const [plan, setPlan] = useState<Plan | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (user) api.get<Plan>("/destinations/plan").then(setPlan).catch((e) => setError(e.message));
  }, [user]);

  async function choose(id: string, overrides: Record<string, number> = {}) {
    setPlan(await api.put<Plan>("/destinations/plan", { destination: id, overrides }));
  }

  function onReply(r: AgentReply) {
    if (r.events.shortlist.length) api.get<Plan>("/destinations/plan").then(setPlan);
    if (r.events.proposals.length) {
      return (
        <div className="flex flex-col gap-2">
          {r.events.proposals.map((p, i) => <ProposalCard key={i} p={p} onApply={() => choose(p.destination, p.overrides)} />)}
        </div>
      );
    }
  }

  if (error) return <p className="text-red-700">{error}</p>;
  if (!plan) return <p className="text-muted">Loading…</p>;

  const w = plan.wedding;
  const est = plan.estimate;
  const maxLine = Math.max(...est.lines.map((l) => l.amount));
  const over = est.total - w.budget;
  const month = new Date(w.date).toLocaleDateString("en-IN", { month: "short", year: "numeric" });

  return (
    <div>
      <h1 className="font-serif text-[38px] font-bold leading-tight">Destination weddings</h1>
      <p className="mt-1 text-sm text-muted">{w.guests} guests · {w.days} days · {month} · total budget {inr(w.budget)}</p>

      <div className="mt-5 grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_380px]">
        <section className="min-w-0">
          <h2 className="text-[17px] font-bold">Your shortlist</h2>
          <div className="mt-3 grid gap-3.5 grid-cols-[repeat(auto-fill,minmax(220px,1fr))]">
            {plan.shortlist.map((d) => (
              <PlaceCard key={d.id} d={d} chosen={d.id === plan.destination} onChoose={() => choose(d.id)} />
            ))}
          </div>

          <div className="card mt-6 p-5">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h2 className="text-[17px] font-bold">Estimated budget: {est.name}</h2>
              <span className="text-[13px] text-muted">{est.guests} guests · {est.days} days · range {inr(est.range[0])}–{inr(est.range[1])}</span>
            </div>
            <div className="mt-4 grid grid-cols-[minmax(150px,1.1fr)_3fr_auto] items-center gap-x-4 gap-y-3 text-sm">
              {est.lines.map((l) => (
                <Line key={l.key} label={l.label} amount={l.amount} pct={(l.amount / maxLine) * 100} edited={l.key in est.overrides} />
              ))}
            </div>
            <div className="mt-4 flex flex-wrap justify-between gap-2 border-t border-line pt-3 text-sm">
              <span>
                Total <b>{inr(est.total)}</b> ·{" "}
                {over > 0 ? <span className="text-warn">{inr(over)} over your {inr(w.budget)} budget</span>
                  : <span className="text-verified">{inr(-over)} under budget</span>}
              </span>
              <span className="text-soft">Based on <b className="text-verified">Verified</b> price bands, valid to {est.source.valid_until}</span>
            </div>
            {Object.keys(est.overrides).length > 0 && (
              <button className="btn-ghost mt-3" onClick={() => choose(est.destination, {})}>Reset to standard estimate</button>
            )}
          </div>
        </section>

        <div className="min-w-0">
          <ChatPanel
            title="Destination planner"
            subtitle="Budgets come from verified price bands"
            endpoint="/destinations/chat"
            greeting={`Tell me the feel you want (palace, beach, hills…) and I'll compare places for ${w.guests} guests with a budget for each.`}
            suggestions={["We want a palace feel", "Compare Udaipur and Goa", `Bring it under ${inr(w.budget)}`, "What if 300 guests?"]}
            placeholder="Ask about places, budgets, dates…"
            onReply={onReply}
          />
        </div>
      </div>
    </div>
  );
}

function PlaceCard({ d, chosen, onChoose }: { d: DestinationCard; chosen: boolean; onChoose: () => void }) {
  return (
    <article className={`card overflow-hidden ${chosen ? "border-2 border-brand" : ""}`}>
      <div className="relative h-[100px] bg-[#e8d8c4]">
        {chosen && <span className="absolute left-2.5 top-2.5 rounded-md bg-white px-2 py-1 text-[11px] font-bold text-brand">Selected</span>}
      </div>
      <div className="px-4 py-3.5">
        <p className="font-serif text-2xl font-bold">{d.name}</p>
        <p className="mt-0.5 text-xs text-soft">{d.vibe}</p>
        <p className="mt-2.5 text-xl font-bold">
          {inr(d.estimate.total)}{" "}
          <span className={`text-xs font-medium ${d.over_budget ? "text-warn" : "text-soft"}`}>{d.over_budget ? "over budget" : "estimated"}</span>
        </p>
        <div className="mt-2 flex flex-col gap-1 text-xs text-ink">
          <span>{d.month} weather: {d.weather}</span>
          <span>{d.travel}</span>
        </div>
        {!chosen && <button className="btn-ghost mt-3 w-full" onClick={onChoose}>See budget</button>}
      </div>
    </article>
  );
}

function Line({ label, amount, pct, edited }: { label: string; amount: number; pct: number; edited: boolean }) {
  return (
    <>
      <span>{label}{edited && <span className="ml-1.5 text-[11px] font-bold text-brand">edited</span>}</span>
      <div className="h-2.5 rounded-full bg-[#f1e8dc]"><div className="h-2.5 rounded-full bg-brand" style={{ width: `${Math.max(pct, 2)}%` }} /></div>
      <span className="text-right font-bold">{inr(amount)}</span>
    </>
  );
}

function ProposalCard({ p, onApply }: { p: Proposal; onApply: () => Promise<void> }) {
  const [state, setState] = useState<"idle" | "applied">("idle");
  return (
    <div className="rounded-[14px] border border-[#f6d6bf] bg-blush px-3.5 py-3 text-sm leading-relaxed">
      <b className="block text-[13px] text-brand-dark">{state === "applied" ? "Applied" : "Suggested change"}</b>
      <span className="mt-1 block">{p.summary}</span>
      <span className="mt-1 block">{p.name}: {inr(p.before_total)} → <b>{inr(p.after_total)}</b></span>
      {state === "idle" && (
        <button className="btn-primary mt-2.5" onClick={async () => { await onApply(); setState("applied"); }}>Apply</button>
      )}
    </div>
  );
}
