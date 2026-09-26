"use client";

/**
 * SWR wrappers around the reads, keyed by instance address so switching
 * DEMO/CANONICAL never shows one instance's data under the other's label.
 * Every screen branches on data, error and loading.
 */
import useSWR from "swr";
import * as api from "./contract";
import { useInstance } from "./instance";

const STABLE = { revalidateOnFocus: false, shouldRetryOnError: true, errorRetryCount: 3 } as const;

function useAddr() {
  return useInstance().address;
}

export function useConfig() {
  const a = useAddr();
  return useSWR(a ? ["config", a] : null, () => api.getConfig(a!), STABLE);
}
export function useStats() {
  const a = useAddr();
  return useSWR(a ? ["stats", a] : null, () => api.getStats(a!), { ...STABLE, refreshInterval: 30_000 });
}
export function usePools() {
  const a = useAddr();
  return useSWR(a ? ["pools", a] : null, () => api.getPools(a!), { ...STABLE, refreshInterval: 30_000 });
}
export function usePool(id: number | null) {
  const a = useAddr();
  return useSWR(a && id ? ["pool", a, id] : null, () => api.getPool(a!, id!), { ...STABLE, refreshInterval: 30_000 });
}
export function usePolicy(id: number | null) {
  const a = useAddr();
  return useSWR(a && id ? ["policy", a, id] : null, () => api.getPolicy(a!, id!), STABLE);
}
export function useClaims() {
  const a = useAddr();
  return useSWR(a ? ["claims", a] : null, () => api.getClaims(a!), { ...STABLE, refreshInterval: 30_000 });
}
export function useClaim(id: number | null, live = false) {
  const a = useAddr();
  return useSWR(a && id ? ["claim", a, id] : null, () => api.getClaim(a!, id!), {
    ...STABLE,
    refreshInterval: live ? 15_000 : 0,
  });
}
export function useBatch(id: number | null) {
  const a = useAddr();
  return useSWR(a && id ? ["batch", a, id] : null, () => api.getBatch(a!, id!), STABLE);
}
export function useBatches() {
  const a = useAddr();
  return useSWR(a ? ["batches", a] : null, () => api.getBatches(a!), STABLE);
}
export function useVerify(id: number | null, enabled: boolean) {
  const a = useAddr();
  return useSWR(a && id && enabled ? ["verify", a, id] : null, () => api.verifyClaim(a!, id!), STABLE);
}
export function useCover(id: number | null) {
  const a = useAddr();
  return useSWR(a && id ? ["cover", a, id] : null, () => api.getCover(a!, id!), STABLE);
}
export function useMyCovers(who: string | null) {
  const a = useAddr();
  return useSWR(a && who ? ["covers-of", a, who.toLowerCase()] : null, () => api.getCoversByBuyer(a!, who!), {
    ...STABLE,
    refreshInterval: 30_000,
  });
}
export function useMyPools(who: string | null) {
  const a = useAddr();
  return useSWR(a && who ? ["pools-of", a, who.toLowerCase()] : null, () => api.getPoolsByUnderwriter(a!, who!), {
    ...STABLE,
    refreshInterval: 30_000,
  });
}
export function usePoolCovers(id: number | null) {
  const a = useAddr();
  return useSWR(a && id ? ["pool-covers", a, id] : null, () => api.getCoversByPool(a!, id!), STABLE);
}
export function usePayout(who: string | null) {
  const a = useAddr();
  return useSWR(a && who ? ["payout", a, who.toLowerCase()] : null, () => api.payoutOf(a!, who!), {
    ...STABLE,
    refreshInterval: 25_000,
  });
}
export function useQuote(pool: number | null, amountWei: bigint | null, days: number) {
  const a = useAddr();
  return useSWR(
    a && pool && amountWei && amountWei > 0n && days > 0 ? ["quote", a, pool, amountWei.toString(), days] : null,
    () => api.quote(a!, pool!, amountWei!, days),
    STABLE,
  );
}
export function useEvidenceCheck(pool: number | null, urls: string) {
  const a = useAddr();
  return useSWR(a && pool && urls.trim() ? ["evidence", a, pool, urls.trim()] : null, () =>
    api.checkEvidence(a!, pool!, urls.trim()),
    STABLE,
  );
}
