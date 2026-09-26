"use client";

import { BookOpen, Code2, HelpCircle, Lock, ShieldAlert, Table } from "lucide-react";
import { PageHead } from "@/components/AppShell";
import { useConfig } from "@/lib/hooks";
import { CANONICAL_ADDRESS, DEMO_ADDRESS, REGISTRY_ADDRESS } from "@/lib/genlayer";
import { BUCKET_LABELS, duration, gen, pct } from "@/lib/format";

const LOOPHOLES = [
  ["Buying cover after an incident is public", "The incident date comes from DeFi Llama's record, never from the claimant. Incident < cover start + waiting period → REJECTED_BACKDATED, and the premium is not refunded."],
  ["Fake evidence from a random blog", "Every URL must be https on the pool's frozen allowlist (subdomain-exact, no userinfo, no ports). An archive snapshot counts only if the archived page is itself allowlisted. Refused in file_claim before any validator runs."],
  ["Underwriter withdrawing before a claim", "Each cover locks collateral until it expires and its claim window closes. withdraw_capacity can only take the unlocked part; close_pool is refused while any cover is live."],
  ["Same cover claimed twice", "One claim per cover, stored on the cover. An INCONCLUSIVE claim is refiled on the same record — never filed again."],
  ["More claims than capacity", "Claims on one incident join a settlement window. After it closes, if approved payouts exceed the collateral locked for those covers, all are scaled by the same factor. Order changes nothing; dust stays with the underwriter."],
  ["Evidence edited after judging", "The claim stores the salient text it was judged on and a content hash over it, the DeFi Llama record and the TVL figures. verify_claim recomputes it; a contest re-reads the stored text, not the live page."],
  ["Contest copying old evidence", "Contest URLs must be new to the claim and the written grounds must add ≥20 characters of sentences the claim never said (verbatim, re-punctuated or repeated text refused). Inside consensus, new pages count only for their novel sentences — none → NOT_NOVEL, verdict held."],
  ["Protocol B's incident on protocol A's cover", "The incident record is looked up by the pool's own DeFi Llama id, and at least one evidence page must name the pool's protocol; otherwise INCONCLUSIVE without a model call."],
  ["Owner pausing to freeze money", "Pause gates create_pool, add_capacity and buy_cover only. Filing, judging, contesting, finalizing, releasing, cancelling, withdrawing, settle_stalled and claim_payout all work while paused — proved by test and on chain."],
  ["Payment that also reads the clock", "Only claim_payout transfers, and it reads no clock. Every clock-reading method only credits a payable balance — the finalize + claim_payout split that keeps Studio Dev's fee simulator honest."],
];

const FAQ = [
  ["Is this real insurance?", "No. It is a parametric protocol on a test network. It pays by incident severity measured from TVL, not by proven personal loss."],
  ["What does the model decide?", "Only the classification: which covered peril or which exclusion the evidence shows, from a bracket the contract computes first. It never sees money, dates or the claimant's statement."],
  ["What if the validators can't agree?", "Nothing changes. The judgement can be retried by anyone; if a claim sits unjudged past the stall window, settle_stalled returns it to FILED and lets the buyer refile — while paused, too."],
  ["Why is there a DEMO instance?", "Real hacks are in the past, and the canonical instance rejects backdated claims. The demo is the same bytes with one constructor value: covers start 1,521 days before purchase, so 2022–2023 incidents can be replayed. It is labelled on every page."],
  ["Where does the premium go?", "It is held until the cover ends. Then it is the underwriter's — whether the cover expired unclaimed, was denied, rejected as backdated, or paid."],
];

export default function DocsPage() {
  const cfg = useConfig();
  const c = cfg.data;
  return (
    <div className="wrap">
      <PageHead eyebrow="Docs" title="How CoverClaim decides">
        {c?.division_of_labour ??
          "GenLayer reads public incident evidence and classifies it against the frozen policy's covered perils and exclusions. Deterministic contract logic enforces capacity, waiting periods, backdating checks, premium accounting, severity payouts, deductibles, and pro-rata splits."}
      </PageHead>

      <div className="stack" style={{ gap: 18 }}>
        <section className="card stack">
          <h3 className="row" style={{ gap: 8 }}><BookOpen size={18} color="var(--orange)" /> How it works</h3>
          <ol className="muted" style={{ margin: 0, paddingLeft: 20, lineHeight: 1.9, fontSize: "0.92rem" }}>
            <li><strong style={{ color: "var(--ink)" }}>Frozen policy.</strong> create_pool validates and writes every term once and hashes it; there is no setter anywhere.</li>
            <li><strong style={{ color: "var(--ink)" }}>Mechanical rejection first.</strong> Capacity, term, per-buyer cap, exact premium, rate limit, claim window, one claim per cover and the evidence allowlist are checked by code before GenLayer runs.</li>
            <li><strong style={{ color: "var(--ink)" }}>GenLayer last.</strong> Each validator fetches DeFi Llama&apos;s incident list and TVL history and the evidence pages, keeps the salient sentences, and computes the bracket. No indicator phrase, or protocol not named → INCONCLUSIVE with no model call. Otherwise the model chooses inside the bracket.</li>
            <li><strong style={{ color: "var(--ink)" }}>Full vector compared.</strong> Classification, peril, exclusion, incident date, protocol match, severity bucket, TVL figures, bracket and content hash exactly; strength within one step. A leader outside its own bracket is refused by arithmetic.</li>
            <li><strong style={{ color: "var(--ink)" }}>Deterministic money.</strong> Backdating, cover end, severity payout, deductible and the pro-rata split, in integers.</li>
          </ol>
        </section>

        <section className="card stack">
          <h3 className="row" style={{ gap: 8 }}><Table size={18} color="var(--orange)" /> Payout table (default)</h3>
          <div className="scroll-x">
            <table className="table">
              <thead><tr><th>Bucket</th><th>TVL drop around the incident</th><th>Payout</th></tr></thead>
              <tbody>
                {(c?.default_payout_table_bps ?? [0, 2500, 5000, 7500, 10000]).map((b, i) => (
                  <tr key={i}><td className="mono">{i}</td><td>{BUCKET_LABELS[i]}</td><td>{pct(b)} of cover, minus the deductible</td></tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="math">
            drop = (TVL on the last day before the incident − lowest TVL in the 7 days from it) / TVL before
            <br />payout = cover × table[bucket] × (1 − deductible) — one integer division, rounded down
            <br />premium = ceil(cover × rate_bps × days / (30 × 10000))
          </div>
        </section>

        <section className="card stack">
          <h3 className="row" style={{ gap: 8 }}><ShieldAlert size={18} color="var(--orange)" /> Loopholes, and how each is closed</h3>
          {LOOPHOLES.map(([t, b], i) => (
            <div key={t} className="stack" style={{ gap: 2, paddingBottom: 10, borderBottom: i < LOOPHOLES.length - 1 ? "1px solid var(--line)" : "none" }}>
              <strong style={{ fontSize: "0.92rem" }}>{i + 1}. {t}</strong>
              <span className="muted" style={{ fontSize: "0.86rem" }}>{b}</span>
            </div>
          ))}
        </section>

        <section className="card stack">
          <h3 className="row" style={{ gap: 8 }}><Code2 size={18} color="var(--orange)" /> Integrate with CoverRegistry</h3>
          <p className="muted" style={{ fontSize: "0.88rem" }}>
            CoverRegistry holds no money (custody false, zero payable methods). It reads CoverClaim&apos;s views, so a lending market or vault can ask whether a wallet&apos;s position is insured right now.
          </p>
          <pre className="math" style={{ margin: 0 }}>{`@gl.contract.interface
class ICoverRegistry:
    class View:
        def is_covered(self, address: str, protocol: str) -> bool: ...
        def get_active_cover(self, address: str) -> typing.Any: ...

# in your contract
covered = ICoverRegistry(REGISTRY).view().is_covered(str(user), "euler-v1")
# True only for an ACTIVE cover past its waiting period and before its end.
# A demo-instance cover is never "in force": it is backdated into 2022.`}</pre>
          <div className="kv" style={{ fontSize: "0.78rem" }}>
            <span>CoverRegistry</span><span className="mono">{REGISTRY_ADDRESS ?? "—"}</span>
            <span>CoverClaim (canonical)</span><span className="mono">{CANONICAL_ADDRESS ?? "—"}</span>
            <span>CoverClaim (DEMO)</span><span className="mono">{DEMO_ADDRESS ?? "—"}</span>
          </div>
        </section>

        {c && (
          <section className="card stack">
            <h3 className="row" style={{ gap: 8 }}><Lock size={18} color="var(--orange)" /> This instance&apos;s constants</h3>
            <p className="muted" style={{ fontSize: "0.86rem" }}>{c.label}</p>
            <div className="kv">
              <span>Claim window after cover end</span><span>{duration(c.claim_window_s)}</span>
              <span>Incident settlement window</span><span>{duration(c.settlement_window_s)}</span>
              <span>Contest window</span><span>{duration(c.contest_window_s)}</span>
              <span>Stall window</span><span>{duration(c.stall_ttl_s)}</span>
              <span>Contest bond</span><span>{gen(c.contest_bond_wei)} GEN</span>
              <span>Min evidence strength to pay</span><span>{c.min_covered_strength}/7</span>
            </div>
          </section>
        )}

        <section className="card stack">
          <h3 className="row" style={{ gap: 8 }}><HelpCircle size={18} color="var(--orange)" /> FAQ</h3>
          {FAQ.map(([q, a]) => (
            <details key={q}>
              <summary style={{ cursor: "pointer", fontWeight: 600, padding: "6px 0" }}>{q}</summary>
              <p className="muted" style={{ fontSize: "0.88rem", paddingBottom: 8 }}>{a}</p>
            </details>
          ))}
        </section>

        <section className="card stack">
          <h3>Honest limitations</h3>
          <ul className="muted" style={{ margin: 0, paddingLeft: 20, fontSize: "0.88rem", lineHeight: 1.8 }}>
            <li>Parametric: pays by incident severity (TVL drop), not proven personal loss. TVL also falls when prices fall.</li>
            <li>Evidence is only as good as the allowlisted sources, and pages are read by plain GET — a JavaScript-only page reads as empty (INCONCLUSIVE).</li>
            <li>Classification is subjective; the bracket bounds it but a model still chooses inside it.</li>
            <li>The DEMO instance uses a fixed 1,521-day backdate to replay real incidents. It is not insurance.</li>
            <li>Studio Dev may queue an on-finalized transfer without executing it; get_stats reports the gap as undelivered_wei rather than hiding it.</li>
          </ul>
        </section>
      </div>
    </div>
  );
}
