"use client";

import { AnimatePresence, motion } from "framer-motion";
import { ArrowRight, Filter, Scale } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";
import { PageHead } from "@/components/AppShell";
import { CardSkeleton, EmptyState, ErrorState } from "@/components/States";
import { toneOf, VerdictBadge, type Tone } from "@/components/Verdict";
import { useClaims } from "@/lib/hooks";
import { date, gen, human } from "@/lib/format";

const FILTERS: { key: "all" | Tone; label: string }[] = [
  { key: "all", label: "All" },
  { key: "covered", label: "Covered" },
  { key: "excluded", label: "Excluded / rejected" },
  { key: "inconclusive", label: "Inconclusive" },
  { key: "pending", label: "Pending" },
];

export default function ClaimsPage() {
  const { data, error, isLoading, mutate } = useClaims();
  const [tone, setTone] = useState<"all" | Tone>("all");
  const [protocol, setProtocol] = useState("all");
  const items = useMemo(() => [...(data?.items ?? [])].reverse(), [data]);
  const protocols = useMemo(() => Array.from(new Set(items.map((c) => c.protocol_name))).sort(), [items]);
  const shown = items.filter((c) => (tone === "all" || toneOf(c.status) === tone) && (protocol === "all" || c.protocol_name === protocol));

  return (
    <div className="wrap">
      <PageHead eyebrow="Claims" title="Every verdict, on chain">
        Classification by GenLayer validators; every consequence — backdating, cover end, severity, deductible, pro-rata — by arithmetic.
      </PageHead>
      <div className="row" style={{ marginBottom: 18, gap: 8 }}>
        <Filter size={14} color="var(--muted)" />
        {FILTERS.map((f) => (
          <button key={f.key} className={`btn btn-sm ${tone === f.key ? "btn-primary" : "btn-ghost"}`} onClick={() => setTone(f.key)}>
            {f.label}
          </button>
        ))}
        <select className="select" value={protocol} onChange={(e) => setProtocol(e.target.value)} style={{ width: "auto", padding: "7px 12px", borderRadius: 999 }} aria-label="Filter by protocol">
          <option value="all">All protocols</option>
          {protocols.map((p) => <option key={p} value={p}>{p}</option>)}
        </select>
      </div>
      {error && <ErrorState retry={() => mutate()} />}
      {isLoading && <div className="stack">{[0, 1, 2].map((i) => <CardSkeleton key={i} lines={2} />)}</div>}
      {!isLoading && !error && shown.length === 0 && <EmptyState title="No claims match">Try another filter.</EmptyState>}
      <div className="stack" style={{ gap: 10 }}>
        <AnimatePresence initial>
          {shown.map((c, i) => (
            <motion.div key={c.claim_id} layout initial={{ opacity: 0, x: -24 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0 }} transition={{ delay: i * 0.04 }}>
              <Link href={`/claim/${c.claim_id}`} className="card card-hover row between" style={{ gap: 14, padding: 16 }}>
                <div className="row" style={{ gap: 14, flex: 1, minWidth: 0 }}>
                  <span className="mono dim" style={{ width: 34 }}>#{c.claim_id}</span>
                  <div className="stack" style={{ gap: 2, minWidth: 0, flex: 1 }}>
                    <strong>{c.protocol_name}</strong>
                    <span className="muted break" style={{ fontSize: "0.8rem" }}>
                      {c.incident_date ? `incident ${c.incident_date}` : `filed ${date(c.filed_at)}`}
                      {c.peril && c.peril !== "NONE" && ` · ${human(c.peril)}`}
                      {c.exclusion && c.exclusion !== "NONE" && ` · ${human(c.exclusion)}`}
                      {c.judged_at > 0 && ` · bucket ${c.severity_bucket}`}
                    </span>
                  </div>
                </div>
                <div className="row" style={{ gap: 10 }}>
                  {c.contest_status && <span className="pill"><Scale size={12} /> contest {c.contest_status.toLowerCase()}</span>}
                  {c.payout_wei !== "0" && <span className="pill" style={{ color: "var(--covered)" }}>{gen(c.payout_wei)} GEN</span>}
                  <VerdictBadge status={c.status} size="sm" />
                  <ArrowRight size={16} color="var(--orange)" />
                </div>
              </Link>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}
