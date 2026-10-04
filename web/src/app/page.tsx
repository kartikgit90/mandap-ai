"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import Shell, { SOON } from "@/components/Shell";
import { api, inr, type Enquiry, type Look, type Plan } from "@/lib/api";
import { useAuth } from "@/lib/auth";

// Demo photos (Unsplash), the same ones used in the Shop the Look catalogue.
const SHOP_PHOTOS = ["photo-1619715613791-89d35b51ff81", "photo-1610173827043-9db50e0d8ef9", "photo-1570055349452-29232699cc63"];

export default function Home() {
  return (
    <Shell>
      <HomeBody />
    </Shell>
  );
}

function HomeBody() {
  const { user } = useAuth();
  const [looks, setLooks] = useState<Look[]>([]);
  const [enquiries, setEnquiries] = useState<Enquiry[]>([]);
  const [plan, setPlan] = useState<Plan | null>(null);

  useEffect(() => {
    if (!user) return;
    api.get<Look[]>("/looks").then(setLooks).catch(() => {});
    api.get<Enquiry[]>("/enquiries").then(setEnquiries).catch(() => {});
    api.get<Plan>("/destinations/plan").then(setPlan).catch(() => {});
  }, [user]);

  const w = plan?.wedding;
  const date = w ? new Date(w.date).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }) : "";

  return (
    <div className="mx-auto max-w-[1120px]">
      <p className="text-sm text-muted">Welcome</p>
      <h1 className="mt-1 font-serif text-[40px] font-bold leading-tight">{w ? `${w.couple}'s wedding` : "Your wedding"}</h1>
      {w && <p className="mt-2 text-[15px] text-muted">{date} · {w.guests} guests · {w.functions.join(", ")} · budget {inr(w.budget)}</p>}

      <div className="mt-6 grid gap-4 grid-cols-[repeat(auto-fit,minmax(320px,1fr))]">
        <Link href="/shop-the-look" className="card overflow-hidden no-underline text-ink flex flex-col hover:border-brand-bright">
          <div className="h-[160px] grid grid-cols-3 gap-0.5 bg-blush">
            {SHOP_PHOTOS.map((id) => (
              // eslint-disable-next-line @next/next/no-img-element
              <img key={id} src={`https://images.unsplash.com/${id}?w=300&h=320&fit=crop&crop=top&auto=format&q=70`} alt="" onError={(e) => { e.currentTarget.style.visibility = "hidden"; }} className="h-full w-full object-cover object-top" />
            ))}
          </div>
          <div className="p-5 flex flex-col gap-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-verified">Live</span>
            <span className="font-serif text-[28px] font-bold leading-tight">Shop the Look</span>
            <span className="text-sm leading-relaxed text-muted">Your AI stylist builds a full look for every function: outfit, jewellery and accessories from designers featured in Wedding Affair. Enquire with brands in one click.</span>
            <span className="mt-1 flex gap-5 text-[13px]"><span><b>{looks.length}</b> looks saved</span><span><b>{enquiries.filter((e) => e.status === "sent").length}</b> enquiries sent</span></span>
            <span className="btn-primary mt-2 self-start">Start styling</span>
          </div>
        </Link>

        <Link href="/destinations" className="card overflow-hidden no-underline text-ink flex flex-col hover:border-brand-bright">
          <div className="h-[160px] grid grid-cols-3 gap-0.5 bg-blush">
            <div className="bg-[#f6d6bf]" /><div className="bg-[#eab48d]" /><div className="bg-brand-bright/80" />
          </div>
          <div className="p-5 flex flex-col gap-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-verified">Live</span>
            <span className="font-serif text-[28px] font-bold leading-tight">Destination weddings</span>
            <span className="text-sm leading-relaxed text-muted">Compare destinations for your guest count and dates, see an estimated budget for each, and ask the planner to bring it within budget.</span>
            <span className="mt-1 flex gap-5 text-[13px]">
              <span><b>{plan?.shortlist.length ?? 0}</b> places shortlisted</span>
              {plan && <span>Leading: <b>{plan.estimate.name}</b> · {inr(plan.estimate.total)}</span>}
            </span>
            <span className="btn-primary mt-2 self-start">Plan destination</span>
          </div>
        </Link>
      </div>

      <h2 className="mt-8 text-lg font-bold">Coming soon</h2>
      <div className="mt-3.5 grid gap-3 grid-cols-[repeat(auto-fill,minmax(200px,1fr))]">
        {SOON.map((s) => (
          <div key={s.label} className="rounded-[14px] border border-dashed border-line-strong bg-cream p-4">
            <span className="block text-[15px] font-bold text-ink">{s.label}</span>
            <span className="mt-1 block text-[13px] text-soft">{s.note}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
