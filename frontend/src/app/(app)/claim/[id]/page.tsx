"use client";

import { motion } from "framer-motion";
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  ExternalLink,
  FileSearch,
  Gavel,
  Hash,
  RefreshCw,
  Scale,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { CardSkeleton, ErrorState } from "@/components/States";
import { TxButton } from "@/components/TxButton";
import { VerdictBadge, VerdictStamp } from "@/components/Verdict";
import { useWallet } from "@/components/WalletProvider";
import { claimPayout, contest, finalizeIncident, judgeClaim, judgeContest, refileClaim, settleStalled } from "@/lib/contract";
import { useBatch, useClaim, useConfig, usePayout, useVerify } from "@/lib/hooks";
import { useInstance } from "@/lib/instance";
import { BUCKET_LABELS, date, dateTime, gen, human, pct, short, toBig, usd } from "@/lib/format";
import type { Claim } from "@/types";

function Finding({ label, value, tone }: { label: string; value: React.ReactNode; tone?: string }) {
  return (
    <div className="card" style={{ padding: 14, background: "var(--bg-2)" }}>
      <div className="muted" style={{ fontSize: "0.74rem", textTransform: "uppercase", letterSpacing: "0.06em" }}>{label}</div>
      <div style={{ fontFamily: "var(--font-head)", fontWeight: 600, fontSize: "1.02rem", color: tone, marginTop: 4 }} className="break">{value}</div>
    </div>
  );
}

function Timeline({ c }: { c: Claim }) {
  const events: { at: number; label: string; tone: string; note?: string }[] = [];
  events.push({ at: c.cover_start, label: "Cover starts", tone: "var(--muted)", note: `waiting period ends ${date(c.waiting_ends)}` });
  if (c.incident_day) events.push({ at: c.incident_day, label: "Incident (DeFi Llama record)", tone: "var(--excluded)" });
  events.push({ at: c.cover_end, label: "Cover ends", tone: "var(--muted)" });
  events.push({ at: c.filed_at, label: "Claim filed", tone: "var(--pending)" });
  if (c.refiles > 0) events.push({ at: c.last_filed_at, label: `Refiled (${c.refiles}×)`, tone: "var(--pending)" });
  if (c.judged_at) events.push({ at: c.judged_at, label: `Judged: ${c.classification}`, tone: "var(--orange)" });
  if (c.contested_at) events.push({ at: c.contested_at, label: "Contested", tone: "var(--pending)" });
  if (c.contest_resolved_at) events.push({ at: c.contest_resolved_at, label: `Contest ${c.contest_status.toLowerCase()}`, tone: "var(--orange)" });
  events.sort((a, b) => a.at - b.at);
  return (
    <div className="stack" style={{ gap: 0 }}>
      {events.map((e, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.08 * i }}
          className="row"
          style={{ alignItems: "flex-start", gap: 12, paddingBottom: 14, position: "relative" }}
        >
          <div style={{ width: 12, display: "flex", flexDirection: "column", alignItems: "center", alignSelf: "stretch" }}>
            <span style={{ width: 10, height: 10, borderRadius: 99, background: e.tone, marginTop: 5, boxShadow: `0 0 10px ${e.tone}` }} />
            {i < events.length - 1 && <span style={{ flex: 1, width: 1, background: "var(--line-2)", marginTop: 4 }} />}
          </div>
          <div className="stack" style={{ gap: 0 }}>
            <strong style={{ fontSize: "0.9rem" }}>{e.label}</strong>
            <span className="muted mono" style={{ fontSize: "0.74rem" }}>{e.at < 1e9 * 1.7 ? date(e.at) : dateTime(e.at)}</span>
            {e.note && <span className="dim" style={{ fontSize: "0.74rem" }}>{e.note}</span>}
          </div>
        </motion.div>
      ))}
    </div>
  );
}

export default function ClaimPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const { address: contract } = useInstance();
  const { account } = useWallet();
  const claim = useClaim(Number.isFinite(id) ? id : null, true);
  const cfg = useConfig();
  const c = claim.data;
  const verify = useVerify(id, Boolean(c && c.judged_at > 0));
  const batch = useBatch(c?.batch_id || null);
  const payout = usePayout(account);
  const [urls, setUrls] = useState("");
  const [grounds, setGrounds] = useState("");
  const [mounted] = useState(() => Math.floor(Date.now() / 1000));

  if (claim.error) return <div className="wrap" style={{ paddingTop: 40 }}><ErrorState retry={() => claim.mutate()} /></div>;
  if (claim.isLoading || !c) return <div className="wrap" style={{ paddingTop: 40 }}><CardSkeleton lines={8} /></div>;
  if (c.found === false) return <div className="wrap" style={{ paddingTop: 40 }}><ErrorState title="No such claim" message={`Claim #${id} does not exist on this instance.`} /></div>;

  const refresh = () => {
    void claim.mutate();
    void verify.mutate();
    void batch.mutate();
    void payout.mutate();
  };
  const me = account?.toLowerCase();
  const judged = c.judged_at > 0;
  const cover = toBig(c.cover_amount_wei);
  const afterDed = (BigInt(c.table_bps) * BigInt(10000 - c.deductible_bps)) / 10000n;
  const canContest = me && c.contestable_by && c.contestable_by.toLowerCase() === me;
  const canRefile = me && c.claimant.toLowerCase() === me && (c.status === "INCONCLUSIVE" || (c.status === "FILED" && c.stalls > 0));
  const now = cfg.data?.now ?? mounted;

  return (
    <div className="wrap">
      <div className="row between" style={{ padding: "32px 0 18px", alignItems: "flex-end" }}>
        <div className="stack" style={{ gap: 6 }}>
          <Link href="/claims" className="muted" style={{ fontSize: "0.82rem" }}>← All claims</Link>
          <span className="eyebrow">Claim #{c.claim_id} · cover #{c.cover_id} · pool #{c.pool_id}</span>
          <h2>{c.protocol_name}</h2>
          <span className="muted mono" style={{ fontSize: "0.78rem" }}>claimant {short(c.claimant)} · underwriter {short(c.underwriter)}</span>
        </div>
        <VerdictBadge status={c.status} />
      </div>

      <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 380px), 1fr))", alignItems: "start" }}>
        <div className="stack" style={{ gap: 16 }}>
          <div className="card stack" style={{ alignItems: "center", textAlign: "center", padding: 28 }}>
            <VerdictStamp status={c.status} caption={judged ? `judged ${dateTime(c.judged_at)}` : "awaiting validators"} />
            <p className="muted" style={{ fontSize: "0.9rem", maxWidth: 520, marginTop: 8 }}>{c.reason || "Not judged yet. Anyone can trigger the judgement; nobody is paid to."}</p>
          </div>

          {judged && (
            <div className="card stack">
              <h3 className="row" style={{ gap: 8 }}><ShieldCheck size={16} color="var(--orange)" /> Validator findings</h3>
              <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 150px), 1fr))", gap: 10 }}>
                <Finding label="Classification" value={c.classification} tone={c.classification === "COVERED" ? "var(--covered)" : c.classification === "EXCLUDED" ? "var(--excluded)" : "var(--inconclusive)"} />
                <Finding label="Matched peril" value={c.peril === "NONE" ? "—" : human(c.peril)} />
                <Finding label="Matched exclusion" value={c.exclusion === "NONE" ? "—" : human(c.exclusion)} />
                <Finding label="Incident date" value={c.incident_date || "—"} />
                <Finding label="Protocol named" value={c.protocol_match ? "yes" : "no"} tone={c.protocol_match ? "var(--covered)" : "var(--excluded)"} />
                <Finding label="Severity bucket" value={`${c.severity_bucket} · ${BUCKET_LABELS[c.severity_bucket]}`} />
                <Finding label="Evidence strength" value={`${c.evidence_strength}/7 (range ${c.strength_range[0]}–${c.strength_range[1]})`} />
                <Finding label="Model called" value={c.model_called ? "yes" : "no — pinned by bracket"} />
              </div>
              <div className="kv">
                <span>Bracket (what the model could choose)</span><span className="mono" style={{ fontSize: "0.78rem" }}>{c.bracket}</span>
                <span>DeFi Llama record</span><span style={{ fontSize: "0.8rem" }}>{c.llama_record}</span>
                <span>TVL before → lowest in 7 days</span><span>{usd(c.tvl_before_usd)} → {usd(c.tvl_low_usd)} ({pct(c.drop_bps)} drop)</span>
              </div>
              {c.pinned && <p className="quote">{c.pinned}</p>}
            </div>
          )}

          {judged && (
            <div className="card stack">
              <h3 className="row" style={{ gap: 8 }}><Scale size={16} color="var(--orange)" /> Payout math, line by line</h3>
              <div className="math">
                1. incident {c.incident_date || "?"} ≥ waiting ends {date(c.waiting_ends)}? {c.incident_day >= c.waiting_ends ? "✓" : "✗ → REJECTED_BACKDATED"}
                <br />2. incident ≤ cover end {date(c.cover_end)}? {c.incident_day && c.incident_day <= c.cover_end ? "✓" : c.incident_day ? "✗ → REJECTED_AFTER_COVER_END" : "—"}
                <br />3. effective classification = {c.effective}{c.effective === "EXCLUDED" ? " → DENIED" : c.effective === "INCONCLUSIVE" ? " → refile" : ""}
                <br />4. TVL drop {pct(c.drop_bps)} → bucket {c.severity_bucket} → table pays {pct(c.table_bps)}
                <br />5. deductible {pct(c.deductible_bps)} → {pct(Number(afterDed))} of cover
                <br />6. gross = {gen(cover)} × {pct(c.table_bps)} × (1 − {pct(c.deductible_bps)}) = <strong style={{ color: "var(--covered)" }}>{gen(c.gross_wei, 6)} GEN</strong>
                {batch.data && batch.data.found !== false && (
                  <>
                    {batch.data.status === "FINALIZED" ? (
                      <>
                        <br />7. incident batch #{batch.data.batch_id}: approved {gen(batch.data.gross_total_wei, 6)} vs locked {gen(batch.data.available_wei, 6)} GEN
                        {batch.data.scaled ? " → SCALED pro-rata" : " → fits, paid in full"}
                        <br />8. paid = <strong style={{ color: "var(--covered)" }}>{gen(c.payout_wei, 6)} GEN</strong>
                      </>
                    ) : (
                      <>
                        <br />7. incident batch #{batch.data.batch_id}: {batch.data.members} claim(s) in the window; totals and any pro-rata scaling are fixed at finalize, after {dateTime(batch.data.closes_at)}
                        <br />8. paid = pending
                      </>
                    )}
                  </>
                )}
              </div>
              {verify.data && (
                <span className="row" style={{ fontSize: "0.78rem", color: verify.data.hash_matches ? "var(--covered)" : "var(--excluded)", gap: 6 }}>
                  <Hash size={13} /> content hash {c.content_hash} {verify.data.hash_matches ? "recomputed from the stored evidence and matches" : "MISMATCH"}; gross recomputed {gen(verify.data.gross_recomputed_wei, 6)} GEN
                </span>
              )}
            </div>
          )}

          <div className="card stack">
            <h3 className="row" style={{ gap: 8 }}><FileSearch size={16} color="var(--orange)" /> Evidence</h3>
            {c.evidence_urls.map((u) => (
              <a key={u} href={u} target="_blank" rel="noreferrer" className="row break mono" style={{ fontSize: "0.8rem", color: "var(--orange-2)", gap: 6 }}>
                <ExternalLink size={12} /> {u}
              </a>
            ))}
            {c.statement && <p className="quote">Claimant: “{c.statement}”</p>}
            {c.digest && (
              <details>
                <summary className="muted" style={{ cursor: "pointer", fontSize: "0.84rem" }}>What the validators read (salient sentences, {c.digest.length} chars)</summary>
                <p className="muted" style={{ fontSize: "0.82rem", marginTop: 8, lineHeight: 1.7 }}>{c.digest}</p>
              </details>
            )}
          </div>
        </div>

        <div className="stack" style={{ gap: 16 }}>
          <div className="card">
            <h3 style={{ marginBottom: 14 }}>Timeline</h3>
            <Timeline c={c} />
          </div>

          <div className="card stack">
            <h3 className="row" style={{ gap: 8 }}><Gavel size={16} color="var(--orange)" /> Contest</h3>
            {c.contest_status ? (
              <>
                <div className="row"><span className="pill">{c.contest_status}</span><span className="muted" style={{ fontSize: "0.8rem" }}>by {short(c.contester)}</span></div>
                {c.contest_statement && <p className="quote">{c.contest_statement}</p>}
                {c.contest_urls.map((u) => <span key={u} className="mono break dim" style={{ fontSize: "0.76rem" }}>{u}</span>)}
                {c.contest_reason && <p className="muted" style={{ fontSize: "0.84rem" }}>{c.contest_reason}</p>}
                {c.contest_novel && (
                  <details>
                    <summary className="muted" style={{ cursor: "pointer", fontSize: "0.82rem" }}>Novel sentences the contest added</summary>
                    <p className="muted" style={{ fontSize: "0.8rem", marginTop: 6 }}>{c.contest_novel}</p>
                  </details>
                )}
                {(c.contest_status === "PENDING" || c.contest_status === "JUDGING") && (
                  <TxButton label="Re-judge with the contest evidence" icon={<RefreshCw size={16} />} send={(a) => judgeContest(contract!, a, c.claim_id)} onDone={refresh} />
                )}
              </>
            ) : c.contestable_by ? (
              <>
                <p className="muted" style={{ fontSize: "0.84rem" }}>
                  The losing side ({short(c.contestable_by)}) may contest once before {dateTime(c.contest_window_closes)}, with a {gen(cfg.data?.contest_bond_wei ?? "0")} GEN bond and NEW evidence. Verbatim, re-punctuated or repeated text is refused before scoring. Flip → bond back; hold → bond to the other side.
                </p>
                {canContest && (
                  <>
                    <textarea className="textarea mono" placeholder="New allowlisted evidence URL(s)" value={urls} onChange={(e) => setUrls(e.target.value)} />
                    <textarea className="textarea" placeholder="What the new evidence shows (must be new text)" value={grounds} onChange={(e) => setGrounds(e.target.value)} />
                    <TxButton
                      label={`Contest · bond ${gen(cfg.data?.contest_bond_wei ?? "0")} GEN`}
                      icon={<Gavel size={16} />}
                      disabled={!urls.trim() || grounds.trim().length < 20}
                      send={(a) => contest(contract!, a, c.claim_id, urls.trim(), grounds, toBig(cfg.data?.contest_bond_wei))}
                      onDone={refresh}
                    />
                  </>
                )}
              </>
            ) : (
              <p className="muted" style={{ fontSize: "0.84rem" }}>{c.status === "INCONCLUSIVE" ? "Inconclusive claims are refiled, not contested." : "Not contestable now."}</p>
            )}
          </div>

          <div className="card stack">
            <h3>Actions</h3>
            <p className="dim" style={{ fontSize: "0.78rem" }}>Judging, settling and unsticking are permissionless and work while the contract is paused.</p>
            {(c.status === "FILED" || c.status === "JUDGING") && (
              <TxButton label="Trigger judgement" icon={<ShieldCheck size={16} />} send={(a) => judgeClaim(contract!, a, c.claim_id)} onDone={refresh} />
            )}
            {(c.status === "FILED" || c.status === "JUDGING" || c.contest_status === "PENDING") && (
              <TxButton className="btn btn-ghost" label="Settle stalled" icon={<Clock size={16} />} send={(a) => settleStalled(contract!, a, c.claim_id)} onDone={refresh} />
            )}
            {batch.data && batch.data.status === "OPEN" && (
              <TxButton
                className="btn btn-ghost"
                label={batch.data.finalizable ? `Finalize incident batch #${batch.data.batch_id}` : `Batch settles ${dateTime(batch.data.closes_at)}`}
                icon={<Scale size={16} />}
                disabled={!batch.data.finalizable || now < batch.data.closes_at}
                send={(a) => finalizeIncident(contract!, a, batch.data!.batch_id)}
                onDone={refresh}
              />
            )}
            {canRefile && (
              <>
                <textarea className="textarea mono" placeholder="New evidence URL(s) — at least one never used on this claim" value={urls} onChange={(e) => setUrls(e.target.value)} />
                <TxButton label="Refile with new evidence" icon={<RefreshCw size={16} />} disabled={!urls.trim()} send={(a) => refileClaim(contract!, a, c.claim_id, urls.trim(), c.statement)} onDone={refresh} />
                <span className="dim" style={{ fontSize: "0.76rem" }}>Refile open until {dateTime(c.refile_until)}.</span>
              </>
            )}
            {payout.data && toBig(payout.data.owed_wei) > 0n && (
              <TxButton label={`Withdraw ${gen(payout.data.owed_wei)} GEN`} icon={<CheckCircle2 size={16} />} send={(a) => claimPayout(contract!, a)} onDone={refresh} />
            )}
            {!account && <span className="dim" style={{ fontSize: "0.8rem" }}>Connect a wallet to act on this claim.</span>}
          </div>

          {c.status === "PAID" && (
            <div className="card row" style={{ borderColor: "rgba(46,229,157,0.3)", gap: 10 }}>
              <CheckCircle2 color="var(--covered)" />
              <span>Paid {gen(c.payout_wei, 6)} GEN to {short(c.claimant)}. The premium became the underwriter&apos;s; the rest of the lock returned to the pool.</span>
            </div>
          )}
          {(c.status === "REJECTED_BACKDATED") && (
            <div className="card row" style={{ borderColor: "rgba(255,77,94,0.3)", gap: 10, alignItems: "flex-start" }}>
              <AlertTriangle color="var(--excluded)" style={{ flexShrink: 0 }} />
              <span className="muted" style={{ fontSize: "0.86rem" }}>The incident predates the cover&apos;s start + waiting period. The cover was valid, so the premium is not refunded — this is the backdating check doing its job.</span>
            </div>
          )}
          {c.status === "DENIED_EXCLUDED" && (
            <div className="card row" style={{ borderColor: "rgba(255,77,94,0.3)", gap: 10, alignItems: "flex-start" }}>
              <XCircle color="var(--excluded)" style={{ flexShrink: 0 }} />
              <span className="muted" style={{ fontSize: "0.86rem" }}>The evidence matches a frozen exclusion ({human(c.exclusion)}). No payout; the cover releases to the underwriter after its claim window.</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
