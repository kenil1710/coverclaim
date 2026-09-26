/** Display helpers. Wei is handled as bigint throughout; never as a float. */

const WEI = 10n ** 18n;

export function toBig(v: string | number | bigint | undefined | null): bigint {
  if (v === undefined || v === null || v === "") return 0n;
  try {
    return BigInt(typeof v === "number" ? Math.trunc(v) : v);
  } catch {
    return 0n;
  }
}

/** "1.2345" GEN from wei, trimmed, at most `dp` decimals. */
export function gen(wei: string | number | bigint | undefined | null, dp = 4): string {
  const n = toBig(wei);
  const neg = n < 0n;
  const a = neg ? -n : n;
  const whole = a / WEI;
  let frac = (a % WEI).toString().padStart(18, "0").slice(0, dp).replace(/0+$/, "");
  if (!frac && a !== 0n && whole === 0n) frac = "0".repeat(dp - 1) + "1";
  return (neg ? "-" : "") + whole.toLocaleString("en-US") + (frac ? "." + frac : "");
}

/** Parse a user-typed GEN amount into wei. Returns null if it is not a number. */
export function parseGen(text: string): bigint | null {
  const t = text.trim();
  if (!/^\d+(\.\d{0,18})?$/.test(t)) return null;
  const [w, f = ""] = t.split(".");
  return BigInt(w) * WEI + BigInt((f + "0".repeat(18)).slice(0, 18));
}

export const pct = (bps: number | undefined) =>
  `${((bps ?? 0) / 100).toFixed((bps ?? 0) % 100 === 0 ? 0 : 2)}%`;

export const short = (addr?: string) =>
  addr && addr.length > 12 ? `${addr.slice(0, 6)}…${addr.slice(-4)}` : addr ?? "";

export function date(epoch?: number): string {
  if (!epoch) return "—";
  return new Date(epoch * 1000).toISOString().slice(0, 10);
}

export function dateTime(epoch?: number): string {
  if (!epoch) return "—";
  return new Date(epoch * 1000).toISOString().replace("T", " ").slice(0, 16) + " UTC";
}

export function duration(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds));
  if (s >= 86400) return `${Math.floor(s / 86400)}d ${Math.floor((s % 86400) / 3600)}h`;
  if (s >= 3600) return `${Math.floor(s / 3600)}h ${Math.floor((s % 3600) / 60)}m`;
  if (s >= 60) return `${Math.floor(s / 60)}m`;
  return `${s}s`;
}

export const usd = (v: string | number) => {
  const n = Number(v);
  if (!Number.isFinite(n) || n < 0) return "—";
  if (n >= 1e9) return `$${(n / 1e9).toFixed(2)}B`;
  if (n >= 1e6) return `$${(n / 1e6).toFixed(1)}M`;
  if (n >= 1e3) return `$${(n / 1e3).toFixed(0)}K`;
  return `$${n.toFixed(0)}`;
};

export const human = (id: string) =>
  id
    .toLowerCase()
    .split("_")
    .map((w) => w[0].toUpperCase() + w.slice(1))
    .join(" ");

export const BUCKET_LABELS = ["< 10%", "10–30%", "30–60%", "60–90%", "≥ 90%"];
