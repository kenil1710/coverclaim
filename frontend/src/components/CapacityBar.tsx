"use client";

import { motion } from "framer-motion";
import { gen, toBig } from "@/lib/format";

/** Capacity used vs free, filling on mount. */
export function CapacityBar({ locked, capital, compact = false }: { locked: string; capital: string; compact?: boolean }) {
  const cap = toBig(capital);
  const lk = toBig(locked);
  const pctUsed = cap > 0n ? Number((lk * 10000n) / cap) / 100 : 0;
  return (
    <div className="stack" style={{ gap: 6 }}>
      <div
        style={{
          height: compact ? 6 : 10,
          borderRadius: 999,
          background: "rgba(237,239,245,0.06)",
          overflow: "hidden",
          border: "1px solid var(--line)",
        }}
        role="progressbar"
        aria-valuenow={pctUsed}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Capacity locked"
      >
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${Math.min(100, pctUsed)}%` }}
          transition={{ duration: 1.1, ease: [0.2, 0.8, 0.2, 1] }}
          style={{
            height: "100%",
            borderRadius: 999,
            background: "linear-gradient(90deg, #ff6b2c, #ffb020)",
            boxShadow: "0 0 16px rgba(255,107,44,0.5)",
          }}
        />
      </div>
      {!compact && (
        <div className="row between" style={{ fontSize: "0.78rem" }}>
          <span className="muted">
            <strong style={{ color: "var(--ink)" }}>{gen(lk)}</strong> GEN locked
          </span>
          <span className="muted">
            <strong style={{ color: "var(--ink)" }}>{gen(cap - lk)}</strong> GEN free · {pctUsed.toFixed(1)}%
          </span>
        </div>
      )}
    </div>
  );
}
