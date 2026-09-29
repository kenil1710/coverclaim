"use client";

import { AnimatePresence, motion } from "framer-motion";
import { ArrowLeft, ArrowRight, Coins, Lock, Plus, ShieldCheck, ShieldX, Wallet } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { PageHead } from "@/components/AppShell";
import { CapacityBar } from "@/components/CapacityBar";
import { CardSkeleton, EmptyState, ErrorState } from "@/components/States";
import { TxButton } from "@/components/TxButton";
import { useWallet } from "@/components/WalletProvider";
import { claimPayout, closePool, createPool, withdrawCapacity, type PoolInput } from "@/lib/contract";
import { useConfig, useMyPools, usePayout } from "@/lib/hooks";
import { useInstance } from "@/lib/instance";
import { BUCKET_LABELS, gen, human, parseGen, pct, toBig } from "@/lib/format";
import type { Pool } from "@/types";

const PERILS = ["SMART_CONTRACT_BUG", "ORACLE_MANIPULATION", "ECONOMIC_EXPLOIT", "BRIDGE_COMPROMISE"];
const EXCLUSIONS = ["PHISHING", "FRONTEND_HIJACK", "USER_KEY_COMPROMISE", "RUG_BY_TEAM", "GOVERNANCE_ATTACK"];
const STEPS = ["Protocol", "Perils", "Pricing", "Evidence", "Review"];

function Toggle({ on, label, tone, onClick }: { on: boolean; label: string; tone: "peril" | "excl"; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`tag ${tone === "peril" ? "tag-peril" : "tag-excl"}`}
      style={{ cursor: "pointer", opacity: on ? 1 : 0.35, padding: "7px 11px", fontSize: "0.78rem" }}
      aria-pressed={on}
    >
      {on ? "✓ " : ""}
      {human(label)}
    </button>
  );
}

function Wizard({ onCreated }: { onCreated: () => void }) {
  const { address: contract } = useInstance();
  const cfg = useConfig();
  const [step, setStep] = useState(0);
  const [f, setF] = useState({
    protocolName: "Euler",
    slug: "euler-v1",
    llamaId: "1183",
    chain: "Ethereum",
    perils: ["SMART_CONTRACT_BUG", "ORACLE_MANIPULATION", "ECONOMIC_EXPLOIT"],
    exclusions: [...EXCLUSIONS],
    rate: "100",
    waiting: "7",
    deductible: "1000",
    maxCover: "2",
    term: "90",
    collateral: "10000",
    table: ["0", "2500", "5000", "7500", "10000"],
    domains: "euler.finance",
    wording: "",
    capacity: "5",
  });
  const set = (k: keyof typeof f, v: unknown) => setF((o) => ({ ...o, [k]: v }));
  const toggle = (k: "perils" | "exclusions", v: string) =>
    set(k, f[k].includes(v) ? f[k].filter((x) => x !== v) : [...f[k], v]);

  const cap = parseGen(f.capacity);
  const maxC = parseGen(f.maxCover);
  const input: PoolInput | null =
    cap && maxC
      ? {
          protocolName: f.protocolName,
          slug: f.slug.trim().toLowerCase(),
          llamaId: f.llamaId.trim(),
          chain: f.chain,
          perils: PERILS.filter((p) => f.perils.includes(p)),
          exclusions: EXCLUSIONS.filter((p) => f.exclusions.includes(p)),
          rateBps: Number(f.rate),
          waitingDays: Number(f.waiting),
          deductibleBps: Number(f.deductible),
          maxCoverWei: maxC,
          termDays: Number(f.term),
          collateralBps: Number(f.collateral),
          payoutTable: f.table.map(Number),
          officialDomains: f.domains,
          wording: f.wording,
          capacityWei: cap,
        }
      : null;

  const field = (label: string, key: keyof typeof f, hint?: string, mono = false) => (
    <label className="stack" style={{ gap: 4 }}>
      <span className="label" style={{ margin: 0 }}>{label}</span>
      <input className={`input ${mono ? "mono" : ""}`} value={f[key] as string} onChange={(e) => set(key, e.target.value)} />
      {hint && <span className="dim" style={{ fontSize: "0.74rem" }}>{hint}</span>}
    </label>
  );

  return (
    <div className="card stack" style={{ borderColor: "rgba(255,107,44,0.3)" }}>
      <div className="row" style={{ gap: 6 }}>
        {STEPS.map((s, i) => (
          <button
            key={s}
            onClick={() => setStep(i)}
            className="pill"
            style={{ cursor: "pointer", color: i === step ? "#120a05" : i < step ? "var(--ink)" : "var(--muted)", background: i === step ? "var(--orange)" : undefined, borderColor: i === step ? "var(--orange)" : undefined }}
          >
            {i + 1}. {s}
          </button>
        ))}
      </div>
      <AnimatePresence mode="wait">
        <motion.div key={step} initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="stack" style={{ gap: 14 }}>
          {step === 0 && (
            <div className="grid g2">
              {field("Protocol name (what the evidence must name)", "protocolName")}
              {field("Chain", "chain")}
              {field("DeFi Llama slug (child protocol)", "slug", "e.g. euler-v1 — severity is measured from api.llama.fi/protocol/<slug>", true)}
              {field("DeFi Llama numeric id", "llamaId", "the `id` in that document; incidents are matched on it", true)}
            </div>
          )}
          {step === 1 && (
            <>
              <div className="stack" style={{ gap: 8 }}>
                <span className="label row" style={{ gap: 6 }}><ShieldCheck size={14} color="var(--covered)" /> Covered perils (at least one)</span>
                <div className="row" style={{ gap: 6 }}>{PERILS.map((p) => <Toggle key={p} on={f.perils.includes(p)} label={p} tone="peril" onClick={() => toggle("perils", p)} />)}</div>
                {f.perils.map((p) => <span key={p} className="dim" style={{ fontSize: "0.76rem" }}>{human(p)}: {cfg.data?.peril_text?.[p]}</span>)}
              </div>
              <div className="stack" style={{ gap: 8 }}>
                <span className="label row" style={{ gap: 6 }}><ShieldX size={14} color="var(--excluded)" /> Exclusions</span>
                <div className="row" style={{ gap: 6 }}>{EXCLUSIONS.map((p) => <Toggle key={p} on={f.exclusions.includes(p)} label={p} tone="excl" onClick={() => toggle("exclusions", p)} />)}</div>
              </div>
            </>
          )}
          {step === 2 && (
            <>
              <div className="grid g3">
                {field("Premium rate (bps per 30 days)", "rate", `${pct(Number(f.rate))} of cover per month`)}
                {field("Waiting period (days)", "waiting", "incidents before start + this are backdated")}
                {field("Deductible (bps)", "deductible", `${pct(Number(f.deductible))} off every payout`)}
                {field("Max cover per buyer (GEN)", "maxCover")}
                {field("Pool term (days, ≤ 365)", "term")}
                {field("Collateral per cover (bps)", "collateral", "10000 = fully collateralised; lower writes more cover and can go pro-rata")}
                {field("Capacity deposit (GEN, min 1)", "capacity")}
              </div>
              <div className="stack" style={{ gap: 6 }}>
                <span className="label">Payout table by severity bucket (bps, non-decreasing)</span>
                <div className="grid g4" style={{ gridTemplateColumns: "repeat(5, minmax(0,1fr))" }}>
                  {f.table.map((v, i) => (
                    <label key={i} className="stack" style={{ gap: 2 }}>
                      <span className="dim" style={{ fontSize: "0.7rem" }}>{BUCKET_LABELS[i]}</span>
                      <input className="input mono" value={v} onChange={(e) => set("table", f.table.map((x, j) => (j === i ? e.target.value : x)))} />
                    </label>
                  ))}
                </div>
              </div>
            </>
          )}
          {step === 3 && (
            <>
              <p className="muted" style={{ fontSize: "0.86rem" }}>
                Every pool allows {(cfg.data?.base_domains ?? ["rekt.news", "web.archive.org"]).join(" and ")} (archive snapshots only of allowlisted pages). Optionally declare the protocol&apos;s domain for post-mortems: it counts only if it IS the website DeFi Llama lists for this protocol (checked by verify_pool; a mismatch fails the pool). Leave it empty to use whatever DeFi Llama lists.
              </p>
              {field("Protocol domain (must match DeFi Llama's listed website; optional)", "domains", undefined, true)}
              <label className="stack" style={{ gap: 4 }}>
                <span className="label" style={{ margin: 0 }}>Underwriter notes (frozen into the wording)</span>
                <textarea className="textarea" maxLength={1500} value={f.wording} onChange={(e) => set("wording", e.target.value)} />
              </label>
            </>
          )}
          {step === 4 && input && (
            <div className="math" style={{ whiteSpace: "pre-wrap" }}>
              {`${input.protocolName} · defillama/${input.slug} (id ${input.llamaId}) · ${input.chain}
Covered: ${input.perils.join(", ")}
Excluded: ${input.exclusions.join(", ") || "none"}
Premium ${pct(input.rateBps)}/30d · waiting ${input.waitingDays}d · deductible ${pct(input.deductibleBps)}
Max cover/buyer ${gen(input.maxCoverWei)} GEN · term ${input.termDays}d · collateral ${pct(input.collateralBps)}
Payout table: ${input.payoutTable.map((b) => pct(b)).join(" / ")}
Evidence: rekt.news, web.archive.org + DeFi Llama's listed website (declared: ${input.officialDomains || "none"}), confirmed by verify_pool before any cover is sold
Capacity: ${gen(input.capacityWei)} GEN

Once created, NOTHING above can be changed — by you or anyone.`}
            </div>
          )}
        </motion.div>
      </AnimatePresence>
      <div className="row between">
        <button className="btn btn-ghost btn-sm" disabled={step === 0} onClick={() => setStep((s) => s - 1)}><ArrowLeft size={14} /> Back</button>
        {step < 4 ? (
          <button className="btn btn-primary btn-sm" onClick={() => setStep((s) => s + 1)}>Next <ArrowRight size={14} /></button>
        ) : (
          <TxButton
            label={`Freeze policy & deposit ${input ? gen(input.capacityWei) : "?"} GEN`}
            icon={<Lock size={16} />}
            disabled={!input || input.perils.length === 0}
            send={(a) => createPool(contract!, a, input!)}
            onDone={(r) => r.status === "OK" && onCreated()}
          />
        )}
      </div>
    </div>
  );
}

function MyPool({ p, refresh }: { p: Pool; refresh: () => void }) {
  const { address: contract } = useInstance();
  const [amt, setAmt] = useState("");
  const w = parseGen(amt);
  return (
    <div className="card stack">
      <div className="row between">
        <Link href={`/pool/${p.pool_id}`}><h3>#{p.pool_id} · {p.protocol_name}</h3></Link>
        <span className="pill">{p.status}</span>
      </div>
      <CapacityBar locked={p.locked_wei} capital={p.capital_wei} />
      <div className="kv">
        <span>Premium earned (released covers)</span><span style={{ color: "var(--covered)" }}>{gen(p.premiums_earned_wei)} GEN</span>
        <span>Premium held (live covers)</span><span>{gen(p.premiums_held_wei)} GEN</span>
        <span>Withdrawable capacity</span><span>{gen(p.free_wei)} GEN</span>
        <span>Paid to claimants</span><span>{gen(p.paid_out_wei)} GEN</span>
        <span>Live covers</span><span>{p.active_covers}</span>
      </div>
      {p.status === "FAILED_VERIFICATION" && <p className="quote">{p.verify_reason}</p>}
      {p.status !== "CLOSED" && (
        <div className="row" style={{ alignItems: "flex-start" }}>
          <input className="input" style={{ maxWidth: 150 }} placeholder="GEN" value={amt} onChange={(e) => setAmt(e.target.value)} aria-label="Amount to withdraw" />
          <TxButton className="btn btn-ghost btn-sm" label="Withdraw unlocked" icon={<Coins size={14} />} disabled={!w || w > toBig(p.free_wei)} send={(a) => withdrawCapacity(contract!, a, p.pool_id, w!)} onDone={refresh} />
          <TxButton className="btn btn-ghost btn-sm" label="Close pool" disabled={p.active_covers > 0} send={(a) => closePool(contract!, a, p.pool_id)} onDone={refresh} />
        </div>
      )}
    </div>
  );
}

export default function UnderwriterPage() {
  const { account, connect } = useWallet();
  const { address: contract } = useInstance();
  const pools = useMyPools(account);
  const payout = usePayout(account);
  const [showWizard, setShowWizard] = useState(false);
  const refresh = () => {
    void pools.mutate();
    void payout.mutate();
  };
  return (
    <div className="wrap">
      <PageHead
        eyebrow="Underwriter"
        title="Provide capacity. Earn premiums."
        right={<button className="btn btn-primary" onClick={() => setShowWizard((s) => !s)}><Plus size={16} /> {showWizard ? "Hide wizard" : "Create pool"}</button>}
      >
        Your capital backs one protocol under wording you freeze. Premium becomes yours when each cover expires unclaimed; capital locked against live covers cannot be withdrawn.
      </PageHead>
      {showWizard && <div style={{ marginBottom: 20 }}><Wizard onCreated={() => { setShowWizard(false); refresh(); }} /></div>}
      {!account ? (
        <EmptyState title="Connect a wallet to see your pools">
          <button className="btn btn-primary" onClick={() => void connect()} style={{ marginTop: 10 }}><Wallet size={14} /> Connect</button>
        </EmptyState>
      ) : (
        <>
          {payout.data && toBig(payout.data.owed_wei) > 0n && (
            <div className="card row between" style={{ marginBottom: 16, borderColor: "rgba(46,229,157,0.3)" }}>
              <span>You can withdraw <strong style={{ color: "var(--covered)" }}>{gen(payout.data.owed_wei)} GEN</strong> (earned premium, withdrawn capacity, returned bonds).</span>
              <TxButton label="Withdraw" icon={<Coins size={16} />} send={(a) => claimPayout(contract!, a)} onDone={refresh} />
            </div>
          )}
          {pools.error && <ErrorState retry={() => pools.mutate()} />}
          {pools.isLoading && <CardSkeleton />}
          {pools.data && pools.data.items.length === 0 && <EmptyState title="No pools from this wallet">Use the wizard to open one.</EmptyState>}
          <div className="grid g2">{pools.data?.items.map((p) => <MyPool key={p.pool_id} p={p} refresh={refresh} />)}</div>
        </>
      )}
    </div>
  );
}
