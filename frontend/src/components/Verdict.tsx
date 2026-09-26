"use client";

import { motion } from "framer-motion";
import { Clock, Shield, ShieldCheck, ShieldQuestion, ShieldX } from "lucide-react";

/** Every claim status mapped onto the four verdict colours. */
export type Tone = "covered" | "excluded" | "inconclusive" | "pending";

export function toneOf(status: string): Tone {
  switch (status) {
    case "APPROVED":
    case "PAID":
      return "covered";
    case "DENIED_EXCLUDED":
    case "REJECTED_BACKDATED":
    case "REJECTED_AFTER_COVER_END":
    case "NO_PAYOUT":
      return "excluded";
    case "INCONCLUSIVE":
      return "inconclusive";
    default:
      return "pending";
  }
}

export const TONE_COLOR: Record<Tone, string> = {
  covered: "var(--covered)",
  excluded: "var(--excluded)",
  inconclusive: "var(--inconclusive)",
  pending: "var(--pending)",
};

const LABEL: Record<string, string> = {
  FILED: "Filed",
  JUDGING: "Judging",
  INCONCLUSIVE: "Inconclusive",
  APPROVED: "Covered · approved",
  NO_PAYOUT: "Covered · 0% bucket",
  DENIED_EXCLUDED: "Excluded",
  REJECTED_BACKDATED: "Backdated",
  REJECTED_AFTER_COVER_END: "After cover end",
  PAID: "Covered · paid",
};

export function statusLabel(s: string) {
  return LABEL[s] ?? s;
}

export function VerdictBadge({ status, size = "md" }: { status: string; size?: "sm" | "md" }) {
  const tone = toneOf(status);
  const color = TONE_COLOR[tone];
  const Icon = tone === "covered" ? ShieldCheck : tone === "excluded" ? ShieldX : tone === "inconclusive" ? ShieldQuestion : Clock;
  return (
    <span
      className="pill"
      style={{
        color,
        borderColor: `color-mix(in srgb, ${color} 40%, transparent)`,
        background: `color-mix(in srgb, ${color} 10%, transparent)`,
        fontSize: size === "sm" ? "0.7rem" : "0.76rem",
      }}
    >
      <Icon size={size === "sm" ? 12 : 14} />
      {statusLabel(status)}
    </span>
  );
}

/** The verdict "stamp": a shield that lands with a thump. */
export function VerdictStamp({ status, caption }: { status: string; caption?: string }) {
  const tone = toneOf(status);
  const color = TONE_COLOR[tone];
  const Icon = tone === "covered" ? ShieldCheck : tone === "excluded" ? ShieldX : tone === "inconclusive" ? ShieldQuestion : Shield;
  return (
    <motion.div
      initial={{ scale: 2.2, opacity: 0, rotate: -14 }}
      animate={{ scale: 1, opacity: 1, rotate: -6 }}
      transition={{ type: "spring", stiffness: 260, damping: 16, delay: 0.15 }}
      style={{
        display: "inline-flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 6,
        padding: "14px 20px",
        border: `2.5px solid ${color}`,
        borderRadius: 14,
        color,
        boxShadow: `0 0 0 6px color-mix(in srgb, ${color} 8%, transparent), 0 18px 50px -18px ${color}`,
        background: `color-mix(in srgb, ${color} 7%, var(--card-solid))`,
        maxWidth: "100%",
      }}
    >
      <Icon size={40} strokeWidth={1.8} />
      <span style={{ fontFamily: "var(--font-head)", fontWeight: 700, letterSpacing: "0.12em", fontSize: "0.9rem", textTransform: "uppercase", textAlign: "center" }}>
        {statusLabel(status)}
      </span>
      {caption && <span style={{ fontSize: "0.72rem", color: "var(--muted)", textAlign: "center" }}>{caption}</span>}
    </motion.div>
  );
}
