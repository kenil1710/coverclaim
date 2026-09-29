/**
 * Typed access to CoverClaim.
 *
 *  1. VIEWS RETURN OBJECTS. Every `@gl.public.view` returns a dict and
 *     genlayer-js hands back a parsed structure (sometimes a Map) - `plain()`
 *     normalises both, so no page ever has to care.
 *
 *  2. NO WRITE EVER THROWS ON CHAIN. A refusal comes back as
 *     `{status: "REJECTED", reason}` with any value already credited to the
 *     sender's payable balance. The UI reads `status`; it never infers a
 *     refusal from an exception.
 *
 *  3. ONE METHOD TRANSFERS. Everything else credits a payable balance, and
 *     `claim_payout` - which reads no clock - sends it. That split is what
 *     keeps every write fee-estimable on Studio Dev.
 */
import { getReadClient, getWalletClient } from "./genlayer";
import type {
  Batch,
  Claim,
  Config,
  Cover,
  EvidenceCheck,
  IncidentCheck,
  LlamaIncident,
  Policy,
  Pool,
  Quote,
  Stats,
  Verification,
  WriteResult,
} from "@/types";

export type Addr = `0x${string}`;
export type TransactionHash = `0x${string}`;

export class ContractReadError extends Error {
  constructor(
    readonly method: string,
    message: string,
    readonly cause?: unknown,
  ) {
    super(message);
    this.name = "ContractReadError";
  }
}

/** Maps (as genlayer-js may decode dicts) and bigint to plain JSON shapes. */
export function plain(value: unknown): unknown {
  if (value instanceof Map) {
    const out: Record<string, unknown> = {};
    for (const [k, v] of value.entries()) out[String(k)] = plain(v);
    return out;
  }
  if (Array.isArray(value)) return value.map(plain);
  if (typeof value === "bigint") {
    return value <= BigInt(Number.MAX_SAFE_INTEGER) && value >= -BigInt(Number.MAX_SAFE_INTEGER)
      ? Number(value)
      : value.toString();
  }
  if (value && typeof value === "object") {
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(value)) out[k] = plain(v);
    return out;
  }
  return value;
}

/** Studio can sit on a read under load; a page that waits forever looks broken. */
const READ_TIMEOUT_MS = 30_000;

async function read<T>(address: Addr, method: string, args: unknown[] = []): Promise<T> {
  try {
    const result = await Promise.race([
      getReadClient().readContract({ address, functionName: method, args: args as never }),
      new Promise<never>((_, reject) =>
        setTimeout(() => reject(new Error(`timed out after ${READ_TIMEOUT_MS / 1000}s`)), READ_TIMEOUT_MS),
      ),
    ]);
    return plain(result) as T;
  } catch (error) {
    throw new ContractReadError(
      method,
      `Could not read ${method}. Studio Dev may be busy — this retries on its own.`,
      error,
    );
  }
}

/* --- reads ------------------------------------------------------------ */

export const getConfig = (a: Addr) => read<Config>(a, "get_config");
export const getStats = (a: Addr) => read<Stats>(a, "get_stats");
export const getPools = (a: Addr) =>
  read<{ total: number; items: Pool[] }>(a, "get_pools", [0, 100]);
export const getPool = (a: Addr, id: number) => read<Pool>(a, "get_pool", [id]);
export const getPolicy = (a: Addr, id: number) => read<Policy>(a, "get_policy", [id]);
export const getPoolsByUnderwriter = (a: Addr, who: string) =>
  read<{ items: Pool[] }>(a, "get_pools_by_underwriter", [who]);
export const getCover = (a: Addr, id: number) => read<Cover>(a, "get_cover", [id]);
export const getCoversByBuyer = (a: Addr, who: string) =>
  read<{ items: Cover[] }>(a, "get_covers_by_buyer", [who]);
export const getCoversByPool = (a: Addr, id: number) =>
  read<{ items: Cover[] }>(a, "get_covers_by_pool", [id]);
export const getClaim = (a: Addr, id: number) => read<Claim>(a, "get_claim", [id]);
export const getClaims = (a: Addr) =>
  read<{ total: number; items: Claim[] }>(a, "get_claims", [0, 100]);
export const getBatch = (a: Addr, id: number) => read<Batch>(a, "get_batch", [id]);
export const getBatches = (a: Addr) =>
  read<{ total: number; items: Batch[] }>(a, "get_batches", [0, 100]);
export const payoutOf = (a: Addr, who: string) =>
  read<{ owed_wei: string; owed_gen: string }>(a, "payout_of", [who]);
export const quote = (a: Addr, pool: number, amountWei: bigint, days: number) =>
  read<Quote>(a, "quote", [pool, amountWei.toString(), days]);
export const checkEvidence = (a: Addr, pool: number, urls: string) =>
  read<EvidenceCheck>(a, "check_evidence", [pool, urls]);
export const verifyClaim = (a: Addr, id: number) => read<Verification>(a, "verify_claim", [id]);
export const checkIncident = (a: Addr, cover: number, key: string) =>
  read<IncidentCheck>(a, "check_incident", [cover, key]);

/**
 * The protocol's incident records inside a window, straight from DeFi Llama -
 * the same list every validator reads. Only a picker: the contract checks the
 * key mechanically and the validators select the record by exact match.
 */
export async function llamaIncidents(llamaId: string, from: string, to: string): Promise<LlamaIncident[]> {
  const res = await fetch("https://api.llama.fi/hacks");
  if (!res.ok) throw new Error(`api.llama.fi/hacks answered ${res.status}`);
  const rows = (await res.json()) as Array<Record<string, unknown>>;
  const out: LlamaIncident[] = [];
  for (const r of rows) {
    if (String(r.defillamaId ?? "") !== llamaId || typeof r.date !== "number") continue;
    const day = new Date(Math.floor(r.date / 86400) * 86400 * 1000).toISOString().slice(0, 10);
    if (day < from || day > to) continue;
    out.push({ key: `${llamaId}:${day}`, date: day, name: String(r.name ?? ""), classification: String(r.classification ?? ""),
      technique: String(r.technique ?? ""), amount: typeof r.amount === "number" ? r.amount : 0 });
  }
  // A day shared by two records needs the name to tell them apart.
  for (const x of out) if (out.filter((y) => y.date === x.date).length > 1) x.key = `${x.key}:${x.name}`;
  return out.sort((a, b) => (a.date < b.date ? -1 : 1));
}

/* --- writes ----------------------------------------------------------- */

/**
 * Fee estimation by simulating the write first. A write that posts an
 * internal message (claim_payout) needs a `messageAllocations` entry naming
 * the real recipient, which only a simulation produces. A failed estimate is
 * not fatal: the node applies its default.
 */
async function estimateFees(
  client: ReturnType<typeof getWalletClient>,
  params: { address: Addr; functionName: string; args: unknown[]; value: bigint },
) {
  try {
    const est = await client.estimateTransactionFeesForWrite({
      address: params.address,
      functionName: params.functionName,
      args: params.args as never,
      value: params.value,
    });
    if (!est?.distribution) return undefined;
    return {
      distribution: est.distribution,
      ...(est.messageAllocations ? { messageAllocations: est.messageAllocations } : {}),
      feeValue: est.feeValue,
    };
  } catch {
    return undefined;
  }
}

async function write(
  contract: Addr,
  account: Addr,
  functionName: string,
  args: unknown[] = [],
  value: bigint = 0n,
): Promise<TransactionHash> {
  const client = getWalletClient(account);
  const fees = await estimateFees(client, { address: contract, functionName, args, value });
  return (await client.writeContract({
    address: contract,
    functionName,
    args: args as never,
    value,
    ...(fees ? { fees } : {}),
  })) as TransactionHash;
}

export type PoolInput = {
  protocolName: string;
  slug: string;
  llamaId: string;
  chain: string;
  perils: string[];
  exclusions: string[];
  rateBps: number;
  waitingDays: number;
  deductibleBps: number;
  maxCoverWei: bigint;
  termDays: number;
  collateralBps: number;
  payoutTable: number[];
  officialDomains: string;
  wording: string;
  capacityWei: bigint;
};

export const createPool = (c: Addr, account: Addr, p: PoolInput) =>
  write(
    c,
    account,
    "create_pool",
    [
      p.protocolName,
      p.slug,
      p.llamaId,
      p.chain,
      p.perils.join(","),
      p.exclusions.join(","),
      p.rateBps,
      p.waitingDays,
      p.deductibleBps,
      p.maxCoverWei.toString(),
      p.termDays,
      p.collateralBps,
      p.payoutTable.join(","),
      p.officialDomains,
      p.wording,
    ],
    p.capacityWei,
  );

/** Permissionless, one consensus round: DeFi Llama confirms slug, id, name and domain. */
export const verifyPool = (c: Addr, account: Addr, pool: number) =>
  write(c, account, "verify_pool", [pool]);
export const addCapacity = (c: Addr, account: Addr, pool: number, wei: bigint) =>
  write(c, account, "add_capacity", [pool], wei);
export const withdrawCapacity = (c: Addr, account: Addr, pool: number, wei: bigint) =>
  write(c, account, "withdraw_capacity", [pool, wei.toString()]);
export const closePool = (c: Addr, account: Addr, pool: number) =>
  write(c, account, "close_pool", [pool]);
export const buyCover = (c: Addr, account: Addr, pool: number, amountWei: bigint, days: number, premiumWei: bigint) =>
  write(c, account, "buy_cover", [pool, amountWei.toString(), days], premiumWei);
export const cancelCover = (c: Addr, account: Addr, cover: number) =>
  write(c, account, "cancel_cover", [cover]);
export const releaseCover = (c: Addr, account: Addr, cover: number) =>
  write(c, account, "release_cover", [cover]);
export const fileClaim = (c: Addr, account: Addr, cover: number, incidentKey: string, urls: string, statement: string) =>
  write(c, account, "file_claim", [cover, incidentKey, urls, statement]);
/** `incidentKey` "" keeps the claim's incident; `urls` "" keeps its evidence. */
export const refileClaim = (c: Addr, account: Addr, claim: number, incidentKey: string, urls: string, statement: string) =>
  write(c, account, "refile_claim", [claim, incidentKey, urls, statement]);
export const judgeClaim = (c: Addr, account: Addr, claim: number) =>
  write(c, account, "judge_claim", [claim]);
export const contest = (c: Addr, account: Addr, claim: number, urls: string, statement: string, bondWei: bigint) =>
  write(c, account, "contest", [claim, urls, statement], bondWei);
export const judgeContest = (c: Addr, account: Addr, claim: number) =>
  write(c, account, "judge_contest", [claim]);
export const finalizeIncident = (c: Addr, account: Addr, batch: number) =>
  write(c, account, "finalize_incident", [batch]);
export const settleStalled = (c: Addr, account: Addr, claim: number) =>
  write(c, account, "settle_stalled", [claim]);
export const claimPayout = (c: Addr, account: Addr) => write(c, account, "claim_payout");

/* --- waiting for a result --------------------------------------------- */

/**
 * Wait for acceptance and read what the contract RETURNED. The receipt's
 * `readable` payload is not always valid JSON (genlayer-js 2.0.0-rc.1 drops
 * commas between map entries), so it is repaired before parsing.
 */
export async function waitForResult(hash: TransactionHash): Promise<WriteResult> {
  const receipt = (await getReadClient().waitForTransactionReceipt({
    hash: hash as never,
    status: "ACCEPTED" as never,
    retries: 300,
    interval: 3000,
  })) as Record<string, unknown>;
  const consensus = receipt?.consensus_data as
    | { leader_receipt?: { result?: { payload?: unknown } }[] }
    | undefined;
  const payload = consensus?.leader_receipt?.[0]?.result?.payload as
    | { readable?: string }
    | string
    | undefined;
  const text = typeof payload === "string" ? payload : payload?.readable;
  if (typeof text === "string") {
    for (const candidate of [text, repairReadable(text)]) {
      try {
        const parsed = JSON.parse(candidate);
        if (parsed && typeof parsed === "object") return parsed as WriteResult;
      } catch {
        /* try the repaired form */
      }
    }
  }
  return { status: "UNKNOWN" };
}

function repairReadable(text: string): string {
  let out = "";
  let inString = false;
  let escaped = false;
  for (const ch of text) {
    if (inString) {
      out += ch;
      if (escaped) escaped = false;
      else if (ch === "\\") escaped = true;
      else if (ch === '"') inString = false;
      continue;
    }
    if (ch === '"') {
      const prev = out.replace(/\s+$/, "").slice(-1);
      if (prev && !"{[,:".includes(prev)) out += ",";
      out += ch;
      inString = true;
      continue;
    }
    out += ch;
  }
  return out;
}
