"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { api, type AgentReply, type ChatMsg, type Source } from "@/lib/api";

type Turn = ChatMsg & { sources?: Source[]; extra?: ReactNode };

/** A chat with one of our agents. The page decides what to do with the agent's cards via onReply. */
export default function ChatPanel({
  title,
  subtitle,
  endpoint,
  context,
  suggestions,
  placeholder,
  greeting,
  onReply,
}: {
  title: string;
  subtitle: string;
  endpoint: string;
  context?: Record<string, unknown>;
  suggestions: string[];
  placeholder: string;
  greeting: string;
  onReply: (r: AgentReply) => ReactNode | void;
}) {
  const [turns, setTurns] = useState<Turn[]>([{ role: "assistant", content: greeting }]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const bottom = useRef<HTMLDivElement>(null);

  // Braces matter: newer Chrome returns a Promise from scrollIntoView, and React
  // would try to call whatever an effect returns as its cleanup ("u is not a function").
  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [turns, busy]);

  async function send(text: string) {
    const msg = text.trim();
    if (!msg || busy) return;
    setInput("");
    setError("");
    const next: Turn[] = [...turns, { role: "user", content: msg }];
    setTurns(next);
    setBusy(true);
    try {
      // The greeting is UI only; the agent sees the real conversation.
      const history = next.slice(1).map(({ role, content }) => ({ role, content }));
      const r = await api.post<AgentReply>(endpoint, { messages: history, context: context ?? {} });
      const extra = onReply(r) || undefined;
      setTurns([...next, { role: "assistant", content: r.reply || "Done.", sources: r.events.sources, extra }]);
    } catch (e) {
      setError((e as Error).message);
      setTurns(turns);
      setInput(msg);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card flex flex-col min-h-[640px] max-h-[calc(100vh-120px)] lg:sticky lg:top-6">
      <div className="flex items-center gap-2.5 border-b border-line px-4 py-3.5">
        <span className="w-[34px] h-[34px] rounded-full bg-blush flex items-center justify-center">
          <svg width="18" height="18" viewBox="0 0 20 20" fill="none" stroke="#7A1F2B" strokeWidth="1.6" aria-hidden><path d="M10 2l1.8 4.6L16.5 8l-4.7 1.4L10 14l-1.8-4.6L3.5 8l4.7-1.4z" /></svg>
        </span>
        <span>
          <span className="block text-[15px] font-bold">{title}</span>
          <span className="block text-xs text-soft">{subtitle}</span>
        </span>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4 flex flex-col gap-3" aria-live="polite">
        {turns.map((t, i) =>
          t.role === "user" ? (
            <div key={i} className="self-end max-w-[88%] rounded-[14px_14px_4px_14px] bg-maroon px-3.5 py-2.5 text-sm leading-relaxed text-white whitespace-pre-wrap">
              {t.content}
            </div>
          ) : (
            <div key={i} className="self-start max-w-[94%] flex flex-col gap-2">
              <div className="rounded-[14px_14px_14px_4px] border border-line bg-cream px-3.5 py-2.5 text-sm leading-relaxed whitespace-pre-wrap">
                {t.content}
              </div>
              {t.extra}
              {!!t.sources?.length && (
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="text-xs text-soft">Sources:</span>
                  {t.sources.map((s) => (
                    <span key={s.title} className="rounded-full border border-line px-2 py-1 text-xs">
                      <b className={s.tier === "verified" ? "text-verified" : "text-published"}>
                        {s.tier === "verified" ? "Verified" : "Published"}
                      </b>{" "}
                      {s.title}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ),
        )}
        {busy && <div className="self-start rounded-[14px] border border-line bg-cream px-3.5 py-2.5 text-sm text-soft">Thinking…</div>}
        {error && <p className="text-sm text-red-700">{error}</p>}
        <div ref={bottom} />
      </div>

      <form className="border-t border-line px-3.5 pt-3 pb-3.5" onSubmit={(e) => { e.preventDefault(); send(input); }}>
        <div className="mb-2.5 flex flex-wrap gap-1.5">
          {suggestions.map((s) => (
            <button key={s} type="button" onClick={() => send(s)} disabled={busy}
              className="rounded-full border border-line-strong bg-cream px-2.5 py-1.5 text-xs hover:border-maroon">
              {s}
            </button>
          ))}
        </div>
        <div className="flex gap-2">
          <label htmlFor={`${endpoint}-input`} className="sr-only">Message</label>
          <input id={`${endpoint}-input`} value={input} onChange={(e) => setInput(e.target.value)} placeholder={placeholder}
            className="flex-1 min-w-0 h-11 rounded-[10px] border border-line-strong bg-cream px-3 text-sm outline-none focus:border-maroon" />
          <button type="submit" aria-label="Send" disabled={busy || !input.trim()} className="btn-primary w-11 h-11 p-0 flex items-center justify-center">
            <svg width="18" height="18" viewBox="0 0 20 20" fill="none" stroke="#FFFFFF" strokeWidth="1.8" aria-hidden><path d="M3 10h13M11 5l5 5-5 5" /></svg>
          </button>
        </div>
      </form>
    </section>
  );
}
