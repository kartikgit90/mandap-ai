"use client";

import { useEffect, useState } from "react";
import ChatPanel from "@/components/ChatPanel";
import Shell from "@/components/Shell";
import { api, inr, type AgentReply, type Enquiry, type Look } from "@/lib/api";
import { useAuth } from "@/lib/auth";

const FUNCTIONS = ["haldi", "mehendi", "sangeet", "pheras", "reception"];
const BUDGETS = [100000, 150000, 250000, 400000, 600000];

// Colour swatches stand in for product photos in the prototype.
const SWATCH: Record<string, string> = {
  emerald: "#1f6b52", green: "#4f8a5b", gold: "#c9a24a", red: "#a3202f", ivory: "#efe6d2", teal: "#2a7d84",
  blue: "#3b6ea8", silver: "#b9bcc2", mint: "#a8d5c2", yellow: "#e9b949", marigold: "#e8902a", pink: "#e7a3b5",
  pastel: "#f2d4dc", parrot: "#6fae3c", white: "#f4f1ea",
};

export default function ShopTheLook() {
  return (
    <Shell>
      <Body />
    </Shell>
  );
}

function Body() {
  const { user } = useAuth();
  const [fn, setFn] = useState("sangeet");
  const [side, setSide] = useState<"bride" | "groom">("bride");
  const [budget, setBudget] = useState(250000);
  const [looks, setLooks] = useState<Look[]>([]);
  const [saved, setSaved] = useState<Look[]>([]);
  const [enquiries, setEnquiries] = useState<Enquiry[]>([]);
  const [tab, setTab] = useState<"new" | "saved" | "enquiries">("new");

  const refresh = () => {
    api.get<Look[]>("/looks").then(setSaved).catch(() => {});
    api.get<Enquiry[]>("/enquiries").then(setEnquiries).catch(() => {});
  };
  useEffect(() => { if (user) refresh(); }, [user]);

  async function save(l: Look) {
    await api.post("/looks", { look: l });
    refresh();
  }

  async function sendEnquiry(id: string) {
    await api.post(`/enquiries/${id}/send`);
    refresh();
  }

  async function discard(id: string) {
    await api.del(`/enquiries/${id}`);
    refresh();
  }

  function onReply(r: AgentReply) {
    if (r.events.looks.length) {
      setLooks(r.events.looks);
      setTab("new");
    }
    if (r.events.drafts.length) {
      refresh();
      return <DraftCards drafts={r.events.drafts} onSend={sendEnquiry} onDiscard={discard} />;
    }
  }

  const shown = tab === "saved" ? saved : looks;

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-serif text-[38px] font-bold leading-tight">Shop the Look</h1>
          <p className="mt-1 text-sm text-muted">Complete looks for every function, from designers featured in Wedding Affair</p>
        </div>
        <div className="flex gap-2" role="tablist">
          <button role="tab" aria-selected={tab === "new"} onClick={() => setTab("new")} className={`btn-ghost ${tab === "new" ? "border-maroon" : ""}`}>Stylist&rsquo;s looks</button>
          <button role="tab" aria-selected={tab === "saved"} onClick={() => setTab("saved")} className={`btn-ghost ${tab === "saved" ? "border-maroon" : ""}`}>Saved ({saved.length})</button>
          <button role="tab" aria-selected={tab === "enquiries"} onClick={() => setTab("enquiries")} className={`btn-ghost ${tab === "enquiries" ? "border-maroon" : ""}`}>Enquiries ({enquiries.length})</button>
        </div>
      </div>

      <div className="mt-5 flex flex-wrap items-start gap-5">
        <section className="flex-[999_1_520px] min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            {FUNCTIONS.map((f) => (
              <button key={f} className="chip capitalize" aria-pressed={fn === f} onClick={() => setFn(f)}>{f}</button>
            ))}
            <span className="mx-1 h-7 w-px bg-line-strong" />
            {(["bride", "groom"] as const).map((s) => (
              <button key={s} className="chip capitalize" aria-pressed={side === s} onClick={() => setSide(s)}>{s}</button>
            ))}
            <label className="ml-auto flex items-center gap-2 text-sm">
              Look budget
              <select value={budget} onChange={(e) => setBudget(Number(e.target.value))} className="rounded-lg border border-line-strong bg-white px-2 py-2 text-sm">
                {BUDGETS.map((b) => <option key={b} value={b}>{inr(b)}</option>)}
              </select>
            </label>
          </div>

          {tab === "enquiries" ? (
            <div className="mt-4 flex flex-col gap-3">
              {enquiries.length === 0 && <Empty text="No enquiries yet. Ask the stylist to contact a brand about a look." />}
              {enquiries.map((e) => (
                <div key={e.id} className="card p-4 flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="font-bold">{e.brand}</p>
                    <p className="text-sm text-muted">{e.items.map((i) => i.name).join(", ")}</p>
                    <p className="mt-1 text-xs text-soft">{e.questions.join(" · ")}</p>
                  </div>
                  {e.status === "sent" ? (
                    <span className="rounded-md bg-[#eef5ef] px-2 py-1 text-xs font-bold text-verified">Sent</span>
                  ) : (
                    <div className="flex gap-2">
                      <button className="btn-primary" onClick={() => sendEnquiry(e.id)}>Send</button>
                      <button className="btn-ghost" onClick={() => discard(e.id)}>Discard</button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : shown.length === 0 ? (
            <Empty text={tab === "saved" ? "No saved looks yet." : `Tell the stylist what you have in mind for the ${fn}, or tap a suggestion.`} />
          ) : (
            <div className="mt-4 grid gap-4 grid-cols-[repeat(auto-fill,minmax(260px,1fr))]">
              {shown.map((l) => (
                <LookCard key={l.id} look={l} budget={budget} onSave={tab === "new" ? () => save(l) : undefined}
                  onDelete={tab === "saved" ? async () => { await api.del(`/looks/${l.id}`); refresh(); } : undefined} />
              ))}
            </div>
          )}
        </section>

        <div className="flex-[1_1_340px] min-w-0 max-w-[440px]">
          <ChatPanel
            title="Your AI stylist"
            subtitle="Only suggests pieces from verified brands"
            endpoint="/stylist/chat"
            context={{ function: fn, side, budget }}
            greeting={`Tell me what you're imagining for your ${fn}: colours, mood, how much you'll be dancing. I'll build complete looks under ${inr(budget)}.`}
            suggestions={[`Build my ${fn} look`, "Something light I can dance in", "Match the groom", "Cheaper options"]}
            placeholder="Describe a look or ask for changes…"
            onReply={onReply}
          />
        </div>
      </div>
    </div>
  );
}

function LookCard({ look, budget, onSave, onDelete }: { look: Look; budget: number; onSave?: () => Promise<void>; onDelete?: () => Promise<void> }) {
  const [state, setState] = useState<"idle" | "busy" | "done">("idle");
  const colors = Array.from(new Set(look.pieces.flatMap((p) => p.colors))).slice(0, 4);
  const over = look.total > budget;
  const seen = look.pieces.find((p) => p.seen_in)?.seen_in;

  return (
    <article className={`card overflow-hidden ${look.top_pick ? "border-2 border-maroon" : ""}`}>
      <div className="relative h-[150px] flex">
        {colors.map((c) => <div key={c} className="flex-1" style={{ background: SWATCH[c] ?? "#e9d9c6" }} />)}
        {look.top_pick && <span className="absolute left-2.5 top-2.5 rounded-md bg-white px-2 py-1 text-[11px] font-bold text-maroon">Stylist&rsquo;s pick</span>}
      </div>
      <div className="p-4">
        <p className="font-serif text-[22px] font-bold leading-tight">{look.title}</p>
        <p className="mt-1 text-xs capitalize text-soft">{look.side} · {look.function}</p>
        {look.why && <p className="mt-2 text-[13px] leading-snug text-muted">{look.why}</p>}
        <div className="mt-3 flex flex-col gap-2 text-[13px]">
          {look.pieces.map((p) => (
            <div key={p.id} className="flex justify-between gap-2">
              <span><b>{p.name}</b> · {p.brand}</span><span className="whitespace-nowrap">{inr(p.price)}</span>
            </div>
          ))}
        </div>
        <div className="mt-3 flex justify-between border-t border-[#f0e6da] pt-2.5 text-sm">
          <span className="text-muted">Full look</span>
          <span className="font-bold">{inr(look.total)} <span className={`font-medium ${over ? "text-warn" : "text-verified"}`}>{over ? "over budget" : "in budget"}</span></span>
        </div>
        {seen && <p className="mt-2 text-xs text-soft">As seen in {seen.issue} · “{seen.title}”</p>}
        <div className="mt-3 flex gap-2">
          {onSave && (
            <button className="btn-ghost flex-1" disabled={state !== "idle"}
              onClick={async () => { setState("busy"); await onSave(); setState("done"); }}>
              {state === "done" ? "Saved" : "Save look"}
            </button>
          )}
          {onDelete && <button className="btn-ghost flex-1" onClick={onDelete}>Remove</button>}
        </div>
      </div>
    </article>
  );
}

function DraftCards({ drafts, onSend, onDiscard }: { drafts: Enquiry[]; onSend: (id: string) => Promise<void>; onDiscard: (id: string) => Promise<void> }) {
  return (
    <div className="flex flex-col gap-2">
      {drafts.map((d) => <Draft key={d.id} d={d} onSend={onSend} onDiscard={onDiscard} />)}
    </div>
  );
}

function Draft({ d, onSend, onDiscard }: { d: Enquiry; onSend: (id: string) => Promise<void>; onDiscard: (id: string) => Promise<void> }) {
  const [state, setState] = useState<"draft" | "sent" | "discarded">("draft");
  return (
    <div className="rounded-[14px] border border-[#f0d9ae] bg-[#fff8ec] px-3.5 py-3 text-sm leading-relaxed">
      <b className="block text-[13px] text-[#8a5a12]">{state === "sent" ? "Sent" : state === "discarded" ? "Discarded" : "Ready to send. Please check:"}</b>
      <span className="mt-1 block">Enquiry to <b>{d.brand}</b> about {d.items.map((i) => i.name).join(", ")}.</span>
      <ul className="mt-1 list-disc pl-5">{d.questions.map((q) => <li key={q}>{q}</li>)}</ul>
      <span className="mt-1 block text-xs text-soft">Shares: {d.shares.join(", ")}. Never shares: {d.never_shares.join(", ")}.</span>
      {state === "draft" && (
        <span className="mt-2.5 flex gap-2">
          <button className="btn-primary" onClick={async () => { await onSend(d.id); setState("sent"); }}>Send enquiry</button>
          <button className="btn-ghost" onClick={async () => { await onDiscard(d.id); setState("discarded"); }}>Discard</button>
        </span>
      )}
    </div>
  );
}

function Empty({ text }: { text: string }) {
  return <div className="mt-4 rounded-2xl border border-dashed border-line-strong bg-white/60 px-6 py-14 text-center text-muted">{text}</div>;
}
