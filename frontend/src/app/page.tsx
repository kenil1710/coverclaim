"use client";

import { motion, type Variants } from "framer-motion";
import {
  ArrowRight,
  Coins,
  FileSearch,
  Gavel,
  Lock,
  Scale,
  Shield,
  ShieldCheck,
  ShieldX,
  Users,
} from "lucide-react";
import Link from "next/link";
import { CountUp } from "@/components/CountUp";
import { Footer } from "@/components/Footer";
import { Logomark, Wordmark } from "@/components/Logo";
import { Skeleton } from "@/components/States";
import { VerdictBadge, VerdictStamp } from "@/components/Verdict";
import { useClaims, useStats } from "@/lib/hooks";
import { BUCKET_LABELS, gen, human, pct, toBig, usd } from "@/lib/format";
import type { Claim } from "@/types";

const fade: Variants = {
  hidden: { opacity: 0, y: 18 },
  show: (i: number) => ({ opacity: 1, y: 0, transition: { delay: 0.08 * i, duration: 0.55, ease: [0.2, 0.8, 0.2, 1] as [number, number, number, number] } }),
};

const STEPS = [
  {
    icon: Lock,
    title: "The policy is frozen",
    body: "An underwriter deposits capacity and fixes the wording: covered perils, exclusions, rate, waiting period, deductible and the payout table. No term can change after a cover is sold.",
  },
  {
    icon: Coins,
    title: "Cover locks capital",
    body: "A buyer pays an exact premium. The collateral for that cover is locked until it expires and its claim window closes — an underwriter cannot withdraw in front of an exploit.",
  },
  {
    icon: FileSearch,
    title: "Validators read the evidence",
    body: "Evidence must come from the pool's frozen allowlist or it is refused before GenLayer runs. Each validator reads DeFi Llama's incident record, its TVL history and the articles, and classifies inside a bracket.",
  },
  {
    icon: Scale,
    title: "Arithmetic pays",
    body: "Backdating, cover end, severity bucket, deductible and the pro-rata split are integer math on stored values. Not one wei is moved by a model.",
  },
];

const WHY = [
  {
    icon: Users,
    title: "No vote by the people who pay",
    body: "Token-holder claim votes ask the payers to judge their own liability. Here independent validators answer one narrow question and a leader cannot forge the answer.",
  },
  {
    icon: Shield,
    title: "The wording is the contract",
    body: "Covered perils and exclusions come from a fixed vocabulary, hashed into the pool at creation. “Was it a bug or user error?” is decided against text nobody can edit.",
  },
  {
    icon: Gavel,
    title: "Every exception has a door",
    body: "Inconclusive claims refile for free. Stalled consensus unsticks while paused. The losing side can contest once with genuinely new evidence. Capacity always drains back to zero.",
  },
];

function ExampleClaim({ claim }: { claim: Claim }) {
  const bucket = claim.severity_bucket;
  return (
    <div className="card" style={{ padding: 0, overflow: "hidden" }}>
      <div className="row between" style={{ padding: "16px 20px", borderBottom: "1px solid var(--line)" }}>
        <div className="row">
          <span className="mono dim">Claim #{claim.claim_id}</span>
          <VerdictBadge status={claim.status} />
        </div>
        <Link href={`/claim/${claim.claim_id}`} className="btn btn-ghost btn-sm">
          Open <ArrowRight size={14} />
        </Link>
      </div>
      <div className="grid g2" style={{ padding: 20, gap: 24 }}>
        <div className="stack">
          <h3>{claim.protocol_name}</h3>
          <p className="muted" style={{ fontSize: "0.88rem" }}>{claim.reason}</p>
          <div className="kv">
            <span>Incident (DeFi Llama)</span>
            <span>{claim.incident_date}</span>
            <span>Matched peril</span>
            <span>{claim.peril !== "NONE" ? human(claim.peril) : "—"}</span>
            <span>TVL before → low</span>
            <span>
              {usd(claim.tvl_before_usd)} → {usd(claim.tvl_low_usd)}
            </span>
            <span>Severity</span>
            <span>
              bucket {bucket} ({BUCKET_LABELS[bucket]} drop) · pays {pct(claim.table_bps)}
            </span>
            <span>Evidence</span>
            <span className="break" style={{ fontSize: "0.8rem" }}>{claim.evidence_urls.join(", ")}</span>
          </div>
        </div>
        <div className="stack" style={{ alignItems: "center", justifyContent: "center", gap: 18 }}>
          <VerdictStamp status={claim.status} caption={`content hash ${claim.content_hash}`} />
          <div className="math" style={{ width: "100%" }}>
            {gen(claim.cover_amount_wei)} GEN cover × {pct(claim.table_bps)} × (1 − {pct(claim.deductible_bps)})
            <br />= <strong style={{ color: "var(--covered)" }}>{gen(claim.gross_wei)} GEN</strong> gross
            {toBig(claim.payout_wei) > 0n && toBig(claim.payout_wei) !== toBig(claim.gross_wei) && (
              <>
                <br />→ {gen(claim.payout_wei)} GEN after the pro-rata split
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function Landing() {
  const stats = useStats();
  const claims = useClaims();
  const example =
    claims.data?.items.find((c) => c.status === "PAID" && c.contest_status === "UPHELD") ??
    claims.data?.items.find((c) => c.status === "PAID") ??
    claims.data?.items.find((c) => c.status === "APPROVED");

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <header style={{ position: "relative", zIndex: 5 }}>
        <div className="wrap row between" style={{ height: 70, flexWrap: "nowrap" }}>
          <Wordmark size={30} />
          <nav className="row" style={{ gap: 6, flexWrap: "nowrap" }}>
            <Link href="/docs" className="hide-sm muted" style={{ padding: "6px 10px" }}>
              How it works
            </Link>
            <Link href="/claims" className="hide-sm muted" style={{ padding: "6px 10px" }}>
              Claims
            </Link>
            <Link href="/pools" className="btn btn-primary btn-sm">
              Launch app <ArrowRight size={14} />
            </Link>
          </nav>
        </div>
      </header>

      <main style={{ flex: 1, position: "relative", zIndex: 1 }}>
        <section className="wrap" style={{ padding: "48px 16px 24px" }}>
          <div className="grid g2" style={{ alignItems: "center", gap: 40 }}>
            <div className="stack" style={{ gap: 22 }}>
              <motion.span className="eyebrow" initial="hidden" animate="show" custom={0} variants={fade}>
                DeFi hack cover · judged by GenLayer
              </motion.span>
              <motion.h1 initial="hidden" animate="show" custom={1} variants={fade}>
                Hacks happen.
                <br />
                <span style={{ color: "var(--orange)" }}>Claims shouldn&apos;t be a vote.</span>
              </motion.h1>
              <motion.p className="muted" style={{ fontSize: "1.1rem", maxWidth: 520 }} initial="hidden" animate="show" custom={2} variants={fade}>
                Frozen policy wording. Independent validators. Automatic payouts.
              </motion.p>
              <motion.div className="row" initial="hidden" animate="show" custom={3} variants={fade}>
                <Link href="/pools" className="btn btn-primary">
                  Browse pools <ArrowRight size={16} />
                </Link>
                <Link href="/claims" className="btn btn-ghost">
                  See real claims
                </Link>
              </motion.div>
            </div>
            <motion.div
              initial={{ opacity: 0, scale: 0.92 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.8, ease: [0.2, 0.8, 0.2, 1] }}
              style={{ display: "flex", justifyContent: "center", position: "relative", minHeight: 300 }}
            >
              <div
                style={{
                  position: "absolute",
                  inset: "10% 15%",
                  background: "radial-gradient(circle, rgba(255,107,44,0.28), transparent 65%)",
                  filter: "blur(20px)",
                }}
              />
              <div style={{ position: "relative" }}>
                <Logomark size={240} animated />
              </div>
              <motion.div
                className="card"
                initial={{ opacity: 0, x: 30 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.9 }}
                style={{ position: "absolute", right: 0, top: 24, padding: "10px 14px", display: "flex", gap: 8, alignItems: "center" }}
              >
                <ShieldCheck size={18} color="var(--covered)" />
                <span style={{ fontSize: "0.8rem" }}>Smart contract bug · covered</span>
              </motion.div>
              <motion.div
                className="card"
                initial={{ opacity: 0, x: -30 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 1.2 }}
                style={{ position: "absolute", left: 0, bottom: 30, padding: "10px 14px", display: "flex", gap: 8, alignItems: "center" }}
              >
                <ShieldX size={18} color="var(--excluded)" />
                <span style={{ fontSize: "0.8rem" }}>DNS hijack · excluded</span>
              </motion.div>
            </motion.div>
          </div>
        </section>

        <section className="wrap section">
          <div className="card" style={{ borderColor: "rgba(255,107,44,0.25)", background: "linear-gradient(135deg, rgba(255,107,44,0.08), rgba(21,21,28,0.8))" }}>
            <span className="eyebrow">The line, in one sentence</span>
            <p style={{ fontSize: "1.08rem", marginTop: 10, lineHeight: 1.7 }}>
              GenLayer reads public incident evidence and classifies it against the frozen policy&apos;s covered perils and exclusions.
              Deterministic contract logic enforces capacity, waiting periods, backdating checks, premium accounting, severity payouts,
              deductibles, and pro-rata splits.
            </p>
          </div>
        </section>

        <section className="wrap section" style={{ paddingTop: 0 }}>
          <div className="stack" style={{ gap: 8, marginBottom: 24 }}>
            <span className="eyebrow">How it works</span>
            <h2>Four steps, one judgement</h2>
          </div>
          <div className="grid g4">
            {STEPS.map((s, i) => (
              <motion.div key={s.title} className="card stack" initial="hidden" animate="show" custom={i} variants={fade}>
                <div className="row between">
                  <s.icon size={22} color="var(--orange)" />
                  <span className="mono dim">0{i + 1}</span>
                </div>
                <h3>{s.title}</h3>
                <p className="muted" style={{ fontSize: "0.88rem" }}>{s.body}</p>
              </motion.div>
            ))}
          </div>
        </section>

        <section className="wrap section" style={{ paddingTop: 0 }}>
          <div className="stack" style={{ gap: 8, marginBottom: 24 }}>
            <span className="eyebrow">Why CoverClaim</span>
            <h2>Built to end the argument</h2>
          </div>
          <div className="grid g3">
            {WHY.map((w, i) => (
              <motion.div key={w.title} className="card stack card-hover" initial="hidden" animate="show" custom={i} variants={fade}>
                <w.icon size={24} color="var(--orange)" />
                <h3>{w.title}</h3>
                <p className="muted" style={{ fontSize: "0.9rem" }}>{w.body}</p>
              </motion.div>
            ))}
          </div>
        </section>

        <section className="wrap section" style={{ paddingTop: 0 }}>
          <div className="row between" style={{ marginBottom: 20 }}>
            <div className="stack" style={{ gap: 8 }}>
              <span className="eyebrow">Live on Studio Dev · demo instance</span>
              <h2>The books, on chain</h2>
            </div>
          </div>
          <div className="grid g4">
            {[
              { label: "Pools", v: stats.data?.pools },
              { label: "Covers sold", v: stats.data?.covers },
              { label: "Claims judged", v: stats.data?.judgements },
              { label: "Contests", v: stats.data?.contests },
            ].map((s) => (
              <div key={s.label} className="card stack" style={{ gap: 4 }}>
                <span className="muted" style={{ fontSize: "0.8rem" }}>{s.label}</span>
                <span className="stat-num">{s.v === undefined ? <Skeleton h={34} w={80} /> : <CountUp value={s.v} />}</span>
              </div>
            ))}
            <div className="card stack" style={{ gap: 4 }}>
              <span className="muted" style={{ fontSize: "0.8rem" }}>Paid out (GEN)</span>
              <span className="stat-num" style={{ color: "var(--covered)" }}>
                {stats.data ? <CountUp value={Number(toBig(stats.data.total_payouts_wei) / 10n ** 14n) / 1e4} decimals={2} /> : <Skeleton h={34} w={80} />}
              </span>
            </div>
            <div className="card stack" style={{ gap: 4 }}>
              <span className="muted" style={{ fontSize: "0.8rem" }}>Capital in pools (GEN)</span>
              <span className="stat-num">
                {stats.data ? <CountUp value={Number(toBig(stats.data.capital_wei) / 10n ** 14n) / 1e4} decimals={2} /> : <Skeleton h={34} w={80} />}
              </span>
            </div>
            <div className="card stack" style={{ gap: 4 }}>
              <span className="muted" style={{ fontSize: "0.8rem" }}>Ledger identity</span>
              <span className="stat-num" style={{ fontSize: "1.3rem", color: stats.data?.ledger_balanced ? "var(--covered)" : "var(--muted)" }}>
                {stats.data ? (stats.data.ledger_balanced && stats.data.held_matches_books ? "balanced" : "check") : <Skeleton h={28} w={100} />}
              </span>
            </div>
            <div className="card stack" style={{ gap: 4 }}>
              <span className="muted" style={{ fontSize: "0.8rem" }}>Pro-rata settlements</span>
              <span className="stat-num">{stats.data ? <CountUp value={stats.data.batches_scaled} /> : <Skeleton h={34} w={60} />}</span>
            </div>
          </div>
        </section>

        <section className="wrap section" style={{ paddingTop: 0 }}>
          <div className="stack" style={{ gap: 8, marginBottom: 20 }}>
            <span className="eyebrow">A real claim, judged on chain</span>
            <h2>Euler, March 2023 — replayed</h2>
            <p className="muted" style={{ maxWidth: 680 }}>
              Seeded on the DEMO instance against DeFi Llama&apos;s own incident record and TVL history and the rekt.news write-up. The
              underwriter contested with new evidence; the verdict held.
            </p>
          </div>
          {example ? (
            <ExampleClaim claim={example} />
          ) : claims.isLoading ? (
            <div className="card stack">
              <Skeleton h={22} w="40%" />
              <Skeleton h={14} />
              <Skeleton h={14} w="70%" />
            </div>
          ) : (
            <div className="card muted">The seeded example will appear here once the demo instance has settled a claim.</div>
          )}
        </section>
      </main>
      <Footer />
    </div>
  );
}
