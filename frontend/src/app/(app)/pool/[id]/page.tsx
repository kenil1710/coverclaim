"use client";

import { motion } from "framer-motion";
import { AlertTriangle, CheckCircle2, Clock, Coins, FileText, Lock, ShieldCheck, ShieldX } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useMemo, useState } from "react";
import { CapacityBar } from "@/components/CapacityBar";
import { CardSkeleton, ErrorState } from "@/components/States";
import { TxButton } from "@/components/TxButton";
import { useWallet } from "@/components/WalletProvider";
import { buyCover, verifyPool } from "@/lib/contract";
import { useConfig, usePolicy, usePool, useQuote } from "@/lib/hooks";
import { useInstance } from "@/lib/instance";
import { BUCKET_LABELS, date, duration, gen, human, parseGen, pct, short, toBig } from "@/lib/format";

/** The same formula the contract uses, for an instant preview while the
 *  chain quote loads: premium = ceil(cover × rate_bps × days / 300000). */
function localPremium(amount: bigint, rateBps: number, days: number): bigint {
  if (amount <= 0n || days <= 0) return 0n;
  const num = amount * BigInt(rateBps) * BigInt(days);
  const den = 300000n;
  return (num + den - 1n) / den;
}

export default function PoolPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const { address: contract, isDemo } = useInstance();
  const { account } = useWallet();
  const pool = usePool(Number.isFinite(id) ? id : null);
  const policy = usePolicy(Number.isFinite(id) ? id : null);
  const cfg = useConfig();
  const [amountText, setAmountText] = useState("1");
  const [days, setDays] = useState(90);
  const amount = parseGen(amountText);
  const quote = useQuote(id, amount, days);
  const [done, setDone] = useState<string | null>(null);
  const [now] = useState(() => Math.floor(Date.now() / 1000));

  const p = pool.data;
  const preview = useMemo(() => (p && amount ? localPremium(amount, p.rate_bps, days) : 0n), [p, amount, days]);

  if (pool.error) return <div className="wrap" style={{ paddingTop: 40 }}><ErrorState retry={() => pool.mutate()} /></div>;
  if (pool.isLoading || !p) return <div className="wrap" style={{ paddingTop: 40 }}><CardSkeleton lines={6} /></div>;
  if (p.found === false) return <div className="wrap" style={{ paddingTop: 40 }}><ErrorState title="No such pool" message={`Pool #${id} does not exist on this instance.`} /></div>;

  const backdate = cfg.data?.demo_backdate_days ?? 0;
  const start = now - backdate * 86400;
  const waitingEnds = start + p.waiting_days * 86400;
  const end = start + days * 86400;
  const premium = quote.data ? toBig(quote.data.premium_wei) : preview;
  const tooMuch = amount !== null && amount > toBig(p.max_cover_wei);
  const maxDays = Math.max(1, Math.min(p.term_days, Math.floor((p.expires_at - start) / 86400)));

  return (
    <div className="wrap">
      <div className="row between" style={{ padding: "32px 0 18px", alignItems: "flex-end" }}>
        <div className="stack" style={{ gap: 6 }}>
          <Link href="/pools" className="muted" style={{ fontSize: "0.82rem" }}>← All pools</Link>
          <span className="eyebrow">Pool #{p.pool_id} · {p.chain}</span>
          <h2>{p.protocol_name}</h2>
          <span className="muted mono" style={{ fontSize: "0.78rem" }}>
            DeFi Llama {p.llama_slug} · id {p.llama_id} · underwriter {short(p.underwriter)}
          </span>
        </div>
        <span className="pill" style={p.selling ? { color: "var(--covered)" } : {}}>
          <Clock size={12} /> {p.status === "CLOSED" ? "Closed" : p.status === "UNVERIFIED" ? "Not verified yet" : p.status === "FAILED_VERIFICATION" ? "Failed verification" : p.seconds_left > 0 ? `${duration(p.seconds_left)} of term left` : "Term ended"}
        </span>
      </div>

      {p.status === "UNVERIFIED" && (
        <div className="card stack" style={{ borderColor: "rgba(255,107,44,0.35)", marginBottom: 16 }}>
          <h3 className="row" style={{ gap: 8 }}><ShieldCheck size={16} color="var(--orange)" /> Not selling until verified</h3>
          <p className="muted" style={{ fontSize: "0.86rem" }}>
            GenLayer validators read DeFi Llama&apos;s record for <span className="mono">{p.llama_slug}</span> once: its id must be {p.llama_id}, its name must be {p.protocol_name}&apos;s, and {p.declared_domain ? <>the declared domain <span className="mono">{p.declared_domain}</span> must be the website it lists</> : <>the website it lists (if any) becomes the protocol domain</>}. No premium can be paid before that. Anyone can trigger it.
          </p>
          <TxButton label="Verify pool against DeFi Llama" icon={<ShieldCheck size={16} />} send={(a) => verifyPool(contract!, a, p.pool_id)} onDone={() => void pool.mutate()} />
        </div>
      )}
      {p.status === "FAILED_VERIFICATION" && (
        <div className="card stack" style={{ borderColor: "var(--excluded)", marginBottom: 16 }}>
          <h3 className="row" style={{ gap: 8 }}><ShieldX size={16} color="var(--excluded)" /> Failed verification — can never sell</h3>
          <p className="quote">{p.verify_reason}</p>
          <p className="muted" style={{ fontSize: "0.84rem" }}>The underwriter can only close it; closing returns their capital.</p>
        </div>
      )}

      <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 380px), 1fr))", alignItems: "start" }}>
        <div className="stack" style={{ gap: 16 }}>
          <div className="card stack">
            <div className="row between">
              <h3 className="row" style={{ gap: 8 }}><Lock size={16} color="var(--orange)" /> Capacity</h3>
              <span className="muted" style={{ fontSize: "0.8rem" }}>{p.active_covers} live covers</span>
            </div>
            <CapacityBar locked={p.locked_wei} capital={p.capital_wei} />
            <div className="kv">
              <span>Collateral per cover</span><span>{pct(p.collateral_bps)} of cover</span>
              <span>Unearned premium held</span><span>{gen(p.premiums_held_wei)} GEN</span>
              <span>Premium earned</span><span>{gen(p.premiums_earned_wei)} GEN</span>
              <span>Paid out</span><span>{gen(p.paid_out_wei)} GEN</span>
            </div>
          </div>

          <div className="card stack">
            <h3 className="row" style={{ gap: 8 }}><ShieldCheck size={16} color="var(--covered)" /> Covered perils</h3>
            {p.perils.map((x) => (
              <div key={x} className="stack" style={{ gap: 2 }}>
                <span className="tag tag-peril" style={{ alignSelf: "flex-start" }}>{human(x)}</span>
                <span className="muted" style={{ fontSize: "0.84rem" }}>{cfg.data?.peril_text?.[x]}</span>
              </div>
            ))}
            <div className="divider" style={{ margin: "4px 0" }} />
            <h3 className="row" style={{ gap: 8 }}><ShieldX size={16} color="var(--excluded)" /> Exclusions</h3>
            {p.exclusions.length === 0 && <span className="muted">None.</span>}
            {p.exclusions.map((x) => (
              <div key={x} className="stack" style={{ gap: 2 }}>
                <span className="tag tag-excl" style={{ alignSelf: "flex-start" }}>{human(x)}</span>
                <span className="muted" style={{ fontSize: "0.84rem" }}>{cfg.data?.exclusion_text?.[x]}</span>
              </div>
            ))}
          </div>

          <div className="card stack">
            <h3>Payout by severity (TVL drop, DeFi Llama)</h3>
            <div className="scroll-x">
              <table className="table">
                <thead>
                  <tr><th>Bucket</th><th>TVL drop</th><th>Pays</th><th>After {pct(p.deductible_bps)} deductible</th></tr>
                </thead>
                <tbody>
                  {p.payout_table_bps.map((b, i) => (
                    <tr key={i}>
                      <td className="mono">{i}</td>
                      <td>{BUCKET_LABELS[i]}</td>
                      <td>{pct(b)}</td>
                      <td style={{ color: b > 0 ? "var(--covered)" : "var(--muted)" }}>{pct(Math.floor((b * (10000 - p.deductible_bps)) / 10000))}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="card stack">
            <h3 className="row" style={{ gap: 8 }}><FileText size={16} color="var(--orange)" /> Frozen policy wording</h3>
            {policy.data ? (
              <>
                <pre className="math" style={{ whiteSpace: "pre-wrap", margin: 0 }}>{policy.data.text}</pre>
                <span className="row" style={{ fontSize: "0.78rem", color: policy.data.hash_matches ? "var(--covered)" : "var(--excluded)" }}>
                  <CheckCircle2 size={14} /> policy hash {policy.data.policy_hash} {policy.data.hash_matches ? "re-derived from stored terms and matches" : "DOES NOT MATCH"}
                </span>
              </>
            ) : (
              <CardSkeleton lines={5} />
            )}
          </div>
        </div>

        <div className="stack" style={{ gap: 16, position: "sticky", top: 80 }}>
          <motion.div className="card stack" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} style={{ borderColor: "rgba(255,107,44,0.3)" }}>
            <h3 className="row" style={{ gap: 8 }}><Coins size={16} color="var(--orange)" /> Buy cover</h3>
            <div className="grid" style={{ gridTemplateColumns: "1fr 1fr" }}>
              <label>
                <span className="label">Cover amount (GEN)</span>
                <input className="input" inputMode="decimal" value={amountText} onChange={(e) => setAmountText(e.target.value)} />
              </label>
              <label>
                <span className="label">Length (days, max {maxDays})</span>
                <input className="input" type="number" min={1} max={maxDays} value={days} onChange={(e) => setDays(Math.max(1, Math.min(maxDays, Number(e.target.value) || 1)))} />
              </label>
            </div>
            <input type="range" min={1} max={maxDays} value={Math.min(days, maxDays)} onChange={(e) => setDays(Number(e.target.value))} aria-label="Cover length in days" style={{ accentColor: "#ff6b2c" }} />
            <div className="math">
              premium = {amount ? gen(amount) : "?"} × {pct(p.rate_bps)} × {days} / 30
              <br />= <strong style={{ color: "var(--orange)" }}>{gen(premium, 8)} GEN</strong>
              {quote.data && <span className="dim"> (quoted by the contract)</span>}
            </div>
            <div className="kv">
              <span>Max cover per buyer</span><span>{gen(p.max_cover_wei)} GEN</span>
              <span>Capital locked for it</span><span>{amount ? gen((amount * BigInt(p.collateral_bps) + 9999n) / 10000n) : "—"} GEN</span>
              <span>Max payout (bucket 4)</span><span>{quote.data ? gen(quote.data.payout_by_bucket_wei[4]) : "—"} GEN</span>
              <span>Cover starts</span><span>{date(start)}{isDemo && backdate > 0 ? " (backdated)" : ""}</span>
              <span>Incidents covered from</span><span style={{ color: "var(--pending)" }}>{date(waitingEnds)}</span>
              <span>Cover ends</span><span>{date(end)}</span>
            </div>
            <div className="row" style={{ alignItems: "flex-start", gap: 8, fontSize: "0.8rem", color: "var(--pending)", background: "rgba(255,176,32,0.07)", border: "1px solid rgba(255,176,32,0.2)", borderRadius: 10, padding: "9px 11px" }}>
              <AlertTriangle size={14} style={{ flexShrink: 0, marginTop: 2 }} />
              <span>
                {p.waiting_days}-day waiting period: an incident dated before {date(waitingEnds)} is rejected as backdated, and the premium is not refunded — the cover was valid, the incident predates it.
                {isDemo && backdate > 0 && ` DEMO: this cover is written as if bought ${backdate} days ago.`}
              </span>
            </div>
            {quote.data && !quote.data.ok && <span style={{ color: "var(--excluded)", fontSize: "0.82rem" }}>The contract would refuse: {quote.data.reason}</span>}
            {tooMuch && <span style={{ color: "var(--excluded)", fontSize: "0.82rem" }}>Above this pool&apos;s max cover per buyer.</span>}
            <TxButton
              label={`Pay ${gen(premium, 6)} GEN premium`}
              icon={<ShieldCheck size={16} />}
              disabled={!p.selling || !amount || premium <= 0n || tooMuch || (quote.data ? !quote.data.ok : false)}
              send={(acct) => buyCover(contract!, acct, p.pool_id, amount!, days, premium)}
              onDone={(r) => {
                if (r.status === "OK") setDone(`Cover #${String(r.cover_id)} bought.`);
                void pool.mutate();
              }}
            />
            {done && (
              <span className="row" style={{ color: "var(--covered)", fontSize: "0.85rem" }}>
                <CheckCircle2 size={14} /> {done} <Link href="/claim" style={{ textDecoration: "underline" }}>File a claim later</Link>
              </span>
            )}
            {!account && <span className="dim" style={{ fontSize: "0.78rem" }}>Connect a wallet on Studio Dev to buy.</span>}
          </motion.div>

          <div className="card stack">
            <h3>Evidence allowlist</h3>
            <p className="muted" style={{ fontSize: "0.84rem" }}>
              A claim or contest on this pool may only cite these domains; anything else is refused before GenLayer runs. The only protocol domain allowed is the website DeFi Llama lists for this protocol, confirmed at verification{p.verified ? (p.protocol_domain ? "" : " — DeFi Llama lists none usable, so only rekt.news counts") : " (pending)"}. DeFi Llama&apos;s incident list and TVL history are read by the contract itself.
            </p>
            <div className="row" style={{ gap: 6 }}>
              {p.evidence_allowlist.map((d) => <span key={d} className="pill mono">{d}</span>)}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
