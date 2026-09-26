"use client";

import { motion } from "framer-motion";
import { ArrowRight, Clock, Layers, Plus } from "lucide-react";
import Link from "next/link";
import { PageHead } from "@/components/AppShell";
import { CapacityBar } from "@/components/CapacityBar";
import { CardSkeleton, EmptyState, ErrorState } from "@/components/States";
import { PerilTags } from "@/components/Tags";
import { usePools } from "@/lib/hooks";
import { duration, gen, pct } from "@/lib/format";
import type { Pool } from "@/types";

function PoolCard({ p, i }: { p: Pool; i: number }) {
  return (
    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}>
      <Link href={`/pool/${p.pool_id}`} className="card card-hover stack" style={{ display: "flex", height: "100%", gap: 14 }}>
        <div className="row between" style={{ alignItems: "flex-start" }}>
          <div className="stack" style={{ gap: 2 }}>
            <span className="mono dim" style={{ fontSize: "0.72rem" }}>POOL #{p.pool_id} · {p.chain}</span>
            <h3 style={{ fontSize: "1.3rem" }}>{p.protocol_name}</h3>
            <span className="mono dim" style={{ fontSize: "0.72rem" }}>defillama/{p.llama_slug}</span>
          </div>
          <span className="pill" style={p.selling ? { color: "var(--covered)", borderColor: "rgba(46,229,157,0.3)" } : {}}>
            {p.status === "CLOSED" ? "Closed" : p.selling ? "Selling" : "Not selling"}
          </span>
        </div>
        <CapacityBar locked={p.locked_wei} capital={p.capital_wei} />
        <div className="grid" style={{ gridTemplateColumns: "repeat(3, minmax(0,1fr))", gap: 8, fontSize: "0.8rem" }}>
          <div className="stack" style={{ gap: 0 }}>
            <span className="muted">Premium</span>
            <strong>{pct(p.rate_bps)}/30d</strong>
          </div>
          <div className="stack" style={{ gap: 0 }}>
            <span className="muted">Deductible</span>
            <strong>{pct(p.deductible_bps)}</strong>
          </div>
          <div className="stack" style={{ gap: 0 }}>
            <span className="muted">Term left</span>
            <strong className="row" style={{ gap: 4 }}>
              <Clock size={12} /> {p.seconds_left > 0 ? duration(p.seconds_left) : "ended"}
            </strong>
          </div>
        </div>
        <PerilTags perils={p.perils} />
        <div className="row between" style={{ marginTop: "auto", fontSize: "0.8rem" }}>
          <span className="muted">
            {p.active_covers} live cover{p.active_covers === 1 ? "" : "s"} · {gen(p.capital_wei)} GEN capital
          </span>
          <ArrowRight size={16} color="var(--orange)" />
        </div>
      </Link>
    </motion.div>
  );
}

export default function PoolsPage() {
  const { data, error, isLoading, mutate } = usePools();
  const pools = data?.items ?? [];
  const open = pools.filter((p) => p.status === "OPEN");
  const closed = pools.filter((p) => p.status !== "OPEN");
  return (
    <div className="wrap">
      <PageHead
        eyebrow="Pools"
        title="Capacity, by protocol"
        right={
          <Link href="/underwriter" className="btn btn-ghost">
            <Plus size={16} /> Open a pool
          </Link>
        }
      >
        Each pool is one underwriter&apos;s capital for one protocol, with its policy wording frozen at creation.
      </PageHead>
      {error && <ErrorState retry={() => mutate()} />}
      {isLoading && (
        <div className="grid g3">
          {[0, 1, 2].map((i) => <CardSkeleton key={i} />)}
        </div>
      )}
      {!isLoading && !error && pools.length === 0 && (
        <EmptyState title="No pools yet">Underwriters open pools from the Underwriter page.</EmptyState>
      )}
      {open.length > 0 && (
        <div className="grid g3">
          {open.map((p, i) => <PoolCard key={p.pool_id} p={p} i={i} />)}
        </div>
      )}
      {closed.length > 0 && (
        <>
          <div className="row" style={{ margin: "36px 0 14px", gap: 8 }}>
            <Layers size={16} color="var(--muted)" />
            <span className="muted">Closed pools — capital returned to the underwriter</span>
          </div>
          <div className="grid g3" style={{ opacity: 0.7 }}>
            {closed.map((p, i) => <PoolCard key={p.pool_id} p={p} i={i} />)}
          </div>
        </>
      )}
    </div>
  );
}
