"use client";

import { CheckCircle2, FileSearch, Link2, ShieldAlert, XCircle } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { PageHead } from "@/components/AppShell";
import { CardSkeleton, EmptyState, ErrorState } from "@/components/States";
import { TxButton } from "@/components/TxButton";
import { VerdictBadge } from "@/components/Verdict";
import { useWallet } from "@/components/WalletProvider";
import { fileClaim } from "@/lib/contract";
import { useEvidenceCheck, useMyCovers, usePool } from "@/lib/hooks";
import { useInstance } from "@/lib/instance";
import { date, gen } from "@/lib/format";

function useDebounced<T>(value: T, ms = 500): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return v;
}

export default function FileClaimPage() {
  const { account, connect } = useWallet();
  const { address: contract } = useInstance();
  const covers = useMyCovers(account);
  const [coverId, setCoverId] = useState<number | null>(null);
  const [urls, setUrls] = useState("");
  const [statement, setStatement] = useState("");
  const [filed, setFiled] = useState<number | null>(null);

  const list = covers.data?.items ?? [];
  const claimable = list.filter((c) => c.claimable);
  const selected = coverId ?? claimable[0]?.cover_id ?? null;
  const cover = list.find((c) => c.cover_id === selected) ?? null;
  const pool = usePool(cover?.pool_id ?? null);
  const debounced = useDebounced(urls);
  const check = useEvidenceCheck(cover?.pool_id ?? null, debounced);

  return (
    <div className="wrap">
      <PageHead eyebrow="File a claim" title="One cover, one claim, allowlisted evidence">
        Evidence must come from the pool&apos;s frozen allowlist. It is checked here as you type — with the contract&apos;s own view — and checked again by the contract before GenLayer is asked anything.
      </PageHead>

      {!account ? (
        <EmptyState title="Connect a wallet to see your covers">
          <button className="btn btn-primary" onClick={() => void connect()} style={{ marginTop: 10 }}>Connect</button>
        </EmptyState>
      ) : covers.error ? (
        <ErrorState retry={() => covers.mutate()} />
      ) : covers.isLoading ? (
        <CardSkeleton />
      ) : list.length === 0 ? (
        <EmptyState title="No covers on this instance">
          Buy cover from a <Link href="/pools" style={{ color: "var(--orange)" }}>pool</Link> first.
        </EmptyState>
      ) : (
        <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 380px), 1fr))", alignItems: "start" }}>
          <div className="card stack">
            <h3>1 · Pick your cover</h3>
            {list.map((c) => (
              <button
                key={c.cover_id}
                onClick={() => c.claimable && setCoverId(c.cover_id)}
                disabled={!c.claimable}
                className="card"
                style={{
                  textAlign: "left",
                  cursor: c.claimable ? "pointer" : "not-allowed",
                  padding: 14,
                  color: "inherit",
                  font: "inherit",
                  borderColor: selected === c.cover_id ? "var(--orange)" : "var(--line)",
                  opacity: c.claimable ? 1 : 0.55,
                }}
              >
                <div className="row between">
                  <strong>#{c.cover_id} · {c.protocol_name}</strong>
                  <span className="pill">{c.claim_id ? `claim #${c.claim_id}` : c.claimable ? "claimable" : c.in_waiting_period ? `waiting until ${date(c.waiting_ends)}` : c.status.toLowerCase()}</span>
                </div>
                <div className="muted" style={{ fontSize: "0.8rem", marginTop: 6 }}>
                  {gen(c.amount_wei)} GEN · covers incidents {date(c.waiting_ends)} → {date(c.end)} · claim by {date(c.claim_deadline)}
                </div>
              </button>
            ))}
          </div>

          <div className="card stack" style={{ borderColor: "rgba(255,107,44,0.3)" }}>
            <h3 className="row" style={{ gap: 8 }}><Link2 size={16} color="var(--orange)" /> 2 · Evidence URLs</h3>
            {pool.data && (
              <div className="row" style={{ gap: 6 }}>
                <span className="muted" style={{ fontSize: "0.8rem" }}>Allowed:</span>
                {pool.data.evidence_allowlist.map((d) => <span key={d} className="pill mono">{d}</span>)}
              </div>
            )}
            <textarea
              className="textarea mono"
              placeholder={"https://rekt.news/euler-rekt\nhttps://web.archive.org/web/2023/https://rekt.news/euler-rekt"}
              value={urls}
              onChange={(e) => setUrls(e.target.value)}
              disabled={!cover}
              aria-label="Evidence URLs, one per line"
            />
            {check.data && (
              <div className="stack" style={{ gap: 6 }}>
                {check.data.items.map((it) => (
                  <div key={it.url} className="row" style={{ alignItems: "flex-start", gap: 8, fontSize: "0.8rem", color: it.ok ? "var(--covered)" : "var(--excluded)" }}>
                    {it.ok ? <CheckCircle2 size={14} style={{ flexShrink: 0, marginTop: 2 }} /> : <XCircle size={14} style={{ flexShrink: 0, marginTop: 2 }} />}
                    <span className="break"><span className="mono">{it.url}</span>{it.reason && <> — {it.reason}</>}</span>
                  </div>
                ))}
                {check.data.reason && <span style={{ color: "var(--excluded)", fontSize: "0.8rem" }}>{check.data.reason}</span>}
              </div>
            )}
            {check.isLoading && urls.trim() && <span className="dim" style={{ fontSize: "0.8rem" }}>Checking against the frozen allowlist…</span>}

            <h3 style={{ marginTop: 6 }}>3 · Statement (optional)</h3>
            <textarea className="textarea" maxLength={600} value={statement} onChange={(e) => setStatement(e.target.value)} placeholder="What happened, in one or two sentences." />
            <p className="dim" style={{ fontSize: "0.76rem" }}>
              Your statement is stored with the claim but is NOT shown to the validators&apos; model — an interested party&apos;s words are not evidence.
            </p>

            <div className="card" style={{ background: "var(--bg-2)", padding: 14 }}>
              <strong className="row" style={{ gap: 6, fontSize: "0.86rem" }}><FileSearch size={14} /> Preview — what happens next</strong>
              <ol className="muted" style={{ fontSize: "0.8rem", margin: "8px 0 0", paddingLeft: 18 }}>
                <li>The contract reads DeFi Llama&apos;s incident record for {cover?.protocol_name ?? "the protocol"} and its TVL history.</li>
                <li>Each validator fetches your pages and keeps only sentences naming the protocol or a risk.</li>
                <li>No risk named, or protocol not named → INCONCLUSIVE, free to refile.</li>
                <li>Otherwise the model picks a covered peril or an exclusion from the bracket.</li>
                <li>Arithmetic applies: waiting period, cover end, severity bucket, deductible, pro-rata.</li>
              </ol>
            </div>
            <TxButton
              label="File claim"
              icon={<ShieldAlert size={16} />}
              disabled={!cover || !check.data?.ok}
              send={(acct) => fileClaim(contract!, acct, cover!.cover_id, urls.trim(), statement)}
              onDone={(r) => {
                if (r.status === "OK") setFiled(Number(r.claim_id));
                void covers.mutate();
              }}
            />
            {filed && (
              <div className="row" style={{ gap: 8 }}>
                <VerdictBadge status="FILED" />
                <Link href={`/claim/${filed}`} className="btn btn-ghost btn-sm">Open claim #{filed} to trigger judging</Link>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
