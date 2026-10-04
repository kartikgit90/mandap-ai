"use client";

import { useEffect, useState, type FormEvent } from "react";
import Shell from "@/components/Shell";
import { api, type KbDoc, type KbHit, type Tier } from "@/lib/api";
import { useAuth } from "@/lib/auth";

const TIERS: { id: Tier; label: string; note: string; cls: string; reachesAi: boolean }[] = [
  { id: "verified", label: "Verified", note: "Editor-checked facts", cls: "bg-[#eef5ef] text-verified", reachesAi: true },
  { id: "published", label: "Published", note: "Magazine articles", cls: "bg-[#edf2f8] text-published", reachesAi: true },
  { id: "internal", label: "Internal", note: "Staff-only notes", cls: "bg-[#fdf3e3] text-[#8a5a12]", reachesAi: false },
  { id: "confidential", label: "Confidential", note: "Contracts, contacts", cls: "bg-[#fbeceb] text-[#a3202f]", reachesAi: false },
];
const tierOf = (t: Tier) => TIERS.find((x) => x.id === t)!;

export default function Knowledge() {
  return (
    <Shell>
      <Body />
    </Shell>
  );
}

function Body() {
  const { user } = useAuth();
  const [docs, setDocs] = useState<KbDoc[] | null>(null);
  const [canEdit, setCanEdit] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = () =>
    api.get<{ can_edit: boolean; docs: KbDoc[] }>("/kb/docs")
      .then((r) => { setDocs(r.docs); setCanEdit(r.can_edit); })
      .catch((e) => setError(e.message));
  useEffect(() => { if (user) load(); }, [user]);

  async function act(fn: () => Promise<unknown>) {
    setError("");
    setBusy(true);
    try { await fn(); await load(); } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }

  const count = (t: Tier) => docs?.filter((d) => d.tier === t).length ?? 0;
  const chunks = docs?.reduce((n, d) => n + d.chunks, 0) ?? 0;

  return (
    <div>
      <h1 className="font-serif text-[38px] font-bold leading-tight">Knowledge base</h1>
      <p className="mt-1 max-w-3xl text-sm text-muted">
        Everything the AI agents know about style and destinations comes from here. Each document is split into short passages and
        searched by meaning (RAG). <b className="text-ink">Only Verified and Published passages ever reach the AI or couples.</b> That
        rule is enforced in code, not left to the AI.
      </p>

      <div className="mt-5 grid gap-3 grid-cols-[repeat(auto-fit,minmax(190px,1fr))]">
        {TIERS.map((t) => (
          <div key={t.id} className="card p-4">
            <span className={`rounded-md px-2 py-1 text-xs font-bold ${t.cls}`}>{t.label}</span>
            <p className="mt-2 text-[26px] font-bold leading-none">{count(t.id)}</p>
            <p className="mt-1 text-xs text-soft">{t.note}</p>
            <p className={`mt-2 text-xs font-bold ${t.reachesAi ? "text-verified" : "text-[#a3202f]"}`}>
              {t.reachesAi ? "✓ AI can use" : "✕ Never sent to the AI"}
            </p>
          </div>
        ))}
      </div>

      {error && <p className="mt-4 rounded-lg bg-[#fbeceb] px-3 py-2 text-sm text-[#a3202f]">{error}</p>}

      <div className="mt-6 grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_380px]">
        <div className="min-w-0 flex flex-col gap-5">
          <SearchTester canEdit={canEdit} />

          <section className="card">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-4 py-3.5">
              <span className="font-bold">Documents <span className="font-normal text-soft">· {docs?.length ?? 0} documents, {chunks} passages</span></span>
              {!canEdit && <span className="text-xs text-soft">Viewing as a couple. Editors can add and re-tier documents.</span>}
              {canEdit && !!docs?.length && (
                <button className="text-xs font-semibold text-brand hover:underline" disabled={busy}
                  onClick={() => act(() => api.post("/kb/seed"))}>{busy ? "Working…" : "Reload demo documents"}</button>
              )}
            </div>
            {docs === null ? (
              <p className="px-4 py-8 text-sm text-soft">Loading…</p>
            ) : docs.length === 0 ? (
              <div className="px-4 py-10 text-center">
                <p className="text-sm text-muted">The knowledge base is empty.</p>
                {canEdit && (
                  <button className="btn-primary mt-3" disabled={busy} onClick={() => act(() => api.post("/kb/seed"))}>
                    {busy ? "Loading…" : "Load demo documents"}
                  </button>
                )}
              </div>
            ) : (
              <ul>
                {docs.map((d) => (
                  <li key={d.id} className="flex flex-wrap items-start gap-3 border-b border-line px-4 py-3 last:border-0">
                    <div className="min-w-0 flex-1">
                      <p className="font-bold">{d.title}</p>
                      <p className="text-xs text-soft">{[d.issue, d.source, `${d.chunks} passage${d.chunks === 1 ? "" : "s"}`].filter(Boolean).join(" · ")}</p>
                      {d.preview && <p className="mt-1 line-clamp-2 text-[13px] text-muted">{d.preview}</p>}
                    </div>
                    {canEdit ? (
                      <div className="flex items-center gap-2">
                        <select aria-label={`Tier for ${d.title}`} value={d.tier} disabled={busy}
                          onChange={(e) => act(() => api.patch(`/kb/docs/${d.id}`, { tier: e.target.value }))}
                          className={`rounded-md border border-line-strong px-2 py-1.5 text-xs font-bold ${tierOf(d.tier).cls}`}>
                          {TIERS.map((t) => <option key={t.id} value={t.id}>{t.label}</option>)}
                        </select>
                        <button className="text-xs text-soft hover:text-[#a3202f]" disabled={busy}
                          onClick={() => confirm(`Delete "${d.title}"?`) && act(() => api.del(`/kb/docs/${d.id}`))}>Delete</button>
                      </div>
                    ) : (
                      <span className={`rounded-md px-2 py-1 text-xs font-bold ${tierOf(d.tier).cls}`}>{tierOf(d.tier).label}</span>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>

        <div className="min-w-0">
          {canEdit ? <AddDoc busy={busy} onAdd={(fn) => act(fn)} /> : <HowItWorks />}
        </div>
      </div>
    </div>
  );
}

function SearchTester({ canEdit }: { canEdit: boolean }) {
  const [q, setQ] = useState("");
  const [res, setRes] = useState<{ hits: KbHit[]; blocked: KbHit[] } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const examples = ["How early should we book a palace in Udaipur?", "What commission does Moti Lane pay?", "What to wear to dance at the sangeet?"];

  async function run(query: string) {
    if (query.trim().length < 2) return;
    setQ(query);
    setBusy(true);
    setError("");
    try { setRes(await api.post("/kb/search", { query })); } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }

  return (
    <section className="card p-4">
      <p className="font-bold">Test the AI&rsquo;s knowledge</p>
      <p className="text-xs text-soft">Ask a question and see exactly which passages the AI would receive, and which the tier rule held back.</p>
      <form className="mt-3 flex gap-2" onSubmit={(e: FormEvent) => { e.preventDefault(); run(q); }}>
        <label htmlFor="kbq" className="sr-only">Question</label>
        <input id="kbq" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Ask anything a couple might ask…"
          className="h-11 min-w-0 flex-1 rounded-[10px] border border-line-strong px-3 text-sm outline-none focus:border-brand" />
        <button className="btn-primary" disabled={busy || q.trim().length < 2}>{busy ? "Searching…" : "Search"}</button>
      </form>
      <div className="mt-2 flex flex-wrap gap-1.5">
        {examples.map((x) => (
          <button key={x} type="button" onClick={() => run(x)} className="rounded-full border border-line-strong px-2.5 py-1 text-xs hover:border-brand-bright">{x}</button>
        ))}
      </div>
      {error && <p className="mt-3 text-sm text-[#a3202f]">{error}</p>}
      {res && (
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-verified">The AI receives ({res.hits.length})</p>
            {res.hits.length === 0 && <p className="mt-2 text-sm text-soft">Nothing relevant in Verified or Published.</p>}
            {res.hits.map((h, i) => <Passage key={i} h={h} />)}
          </div>
          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-[#a3202f]">Held back by the tier rule ({res.blocked.length})</p>
            {res.blocked.length === 0 && <p className="mt-2 text-sm text-soft">Nothing hidden matched.</p>}
            {res.blocked.map((h, i) => <Passage key={i} h={h} hidden={!canEdit} />)}
          </div>
        </div>
      )}
    </section>
  );
}

function Passage({ h, hidden }: { h: KbHit; hidden?: boolean }) {
  const t = tierOf(h.tier);
  return (
    <div className="mt-2 rounded-xl border border-line p-3 text-[13px]">
      <div className="flex items-center gap-2">
        <span className={`rounded px-1.5 py-0.5 text-[11px] font-bold ${t.cls}`}>{t.label}</span>
        <span className="min-w-0 flex-1 truncate font-bold">{h.title}</span>
        <span className="text-[11px] text-soft" title="How close in meaning, 0 to 1">{Math.round(h.score * 100)}% match</span>
      </div>
      <p className="mt-1.5 leading-snug text-muted">{hidden ? "Text hidden. Only editors can read internal and confidential material." : h.text}</p>
    </div>
  );
}

function AddDoc({ busy, onAdd }: { busy: boolean; onAdd: (fn: () => Promise<unknown>) => void }) {
  const [mode, setMode] = useState<"paste" | "file">("paste");
  const [title, setTitle] = useState("");
  const [issue, setIssue] = useState("");
  const [tier, setTier] = useState<Tier>("published");
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);

  const ready = title.trim().length >= 2 && (mode === "paste" ? text.trim().length >= 20 : !!file);

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!ready) return;
    onAdd(async () => {
      if (mode === "paste") {
        await api.post("/kb/docs", { title, issue, tier, text });
      } else {
        const f = new FormData();
        f.append("file", file!);
        f.append("title", title);
        f.append("issue", issue);
        f.append("tier", tier);
        await api.upload("/kb/upload", f);
      }
      setTitle(""); setIssue(""); setText(""); setFile(null);
    });
  }

  const field = "w-full rounded-lg border border-line-strong px-3 py-2.5 text-sm outline-none focus:border-brand";
  return (
    <form onSubmit={submit} className="card p-4 flex flex-col gap-2.5 lg:sticky lg:top-6">
      <p className="font-bold">Add a document</p>
      <div className="flex gap-2">
        <button type="button" className="chip" aria-pressed={mode === "paste"} onClick={() => setMode("paste")}>Paste text</button>
        <button type="button" className="chip" aria-pressed={mode === "file"} onClick={() => setMode("file")}>Upload file</button>
      </div>
      <label className="text-xs font-bold text-muted" htmlFor="kt">Title</label>
      <input id="kt" className={field} value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Mehendi colour guide" />
      <label className="text-xs font-bold text-muted" htmlFor="ki">Issue or source (optional)</label>
      <input id="ki" className={field} value={issue} onChange={(e) => setIssue(e.target.value)} placeholder="e.g. Dec 2026" />
      <label className="text-xs font-bold text-muted" htmlFor="ktier">Trust tier</label>
      <select id="ktier" className={field} value={tier} onChange={(e) => setTier(e.target.value as Tier)}>
        {TIERS.map((t) => <option key={t.id} value={t.id}>{t.label}: {t.note}{t.reachesAi ? "" : " (hidden from AI)"}</option>)}
      </select>
      {mode === "paste" ? (
        <>
          <label className="text-xs font-bold text-muted" htmlFor="ktext">Text</label>
          <textarea id="ktext" className={`${field} min-h-[180px]`} value={text} onChange={(e) => setText(e.target.value)} placeholder="Paste the article here…" />
        </>
      ) : (
        <>
          <label className="text-xs font-bold text-muted" htmlFor="kfile">File (.txt, .md or .pdf, up to 5 MB)</label>
          <input id="kfile" type="file" accept=".txt,.md,.pdf" onChange={(e) => setFile(e.target.files?.[0] ?? null)} className="text-sm" />
        </>
      )}
      <button className="btn-primary mt-1" disabled={busy || !ready}>{busy ? "Adding…" : "Add to knowledge base"}</button>
      <p className="text-xs text-soft">It&rsquo;s split into passages and indexed by meaning. The agents can use it straight away if it&rsquo;s Verified or Published.</p>
    </form>
  );
}

function HowItWorks() {
  const steps = [
    ["Upload", "Editors add articles, fact sheets and notes, and choose a trust tier."],
    ["Split", "Each document is split into short passages of a few sentences."],
    ["Index by meaning", "Google's embedding model turns each passage into numbers that capture its meaning."],
    ["Search", "When a couple asks something, the agent finds the closest passages, from Verified and Published only."],
    ["Answer with sources", "The agent answers from those passages and shows where each fact came from."],
  ];
  return (
    <section className="card p-4">
      <p className="font-bold">How it works</p>
      <ol className="mt-3 flex flex-col gap-3">
        {steps.map(([t, d], i) => (
          <li key={t} className="flex gap-3 text-[13px]">
            <span className="flex h-6 w-6 flex-none items-center justify-center rounded-full bg-blush text-xs font-bold text-brand">{i + 1}</span>
            <span><b>{t}.</b> <span className="text-muted">{d}</span></span>
          </li>
        ))}
      </ol>
    </section>
  );
}
