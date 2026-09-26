"use client";

/**
 * Which CoverClaim instance the app is looking at.
 *
 * DEMO is the default because it holds the seeded claims against real
 * historical incidents; CANONICAL enforces backdating strictly and is where a
 * real cover would be bought. Both are the SAME BYTES; the instance is always
 * named on screen. The choice is remembered per browser, and a failed storage
 * read simply falls back to DEMO.
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { CANONICAL_ADDRESS, DEMO_ADDRESS } from "./genlayer";
import type { Addr } from "./contract";

export type InstanceName = "demo" | "canonical";

type InstanceState = {
  name: InstanceName;
  address: Addr | null;
  isDemo: boolean;
  setName: (n: InstanceName) => void;
  available: InstanceName[];
};

const Ctx = createContext<InstanceState | null>(null);
const KEY = "coverclaim.instance";

export function InstanceProvider({ children }: { children: React.ReactNode }) {
  const available: InstanceName[] = [
    ...(DEMO_ADDRESS ? (["demo"] as const) : []),
    ...(CANONICAL_ADDRESS ? (["canonical"] as const) : []),
  ];
  const [name, setNameState] = useState<InstanceName>(available[0] ?? "demo");

  useEffect(() => {
    try {
      const saved = window.localStorage.getItem(KEY);
      if (saved === "demo" || saved === "canonical") {
        if ((saved === "demo" && DEMO_ADDRESS) || (saved === "canonical" && CANONICAL_ADDRESS)) {
          // Restoring a choice from browser storage after hydration: reading it
          // during render would make the server and client HTML differ.
          // eslint-disable-next-line react-hooks/set-state-in-effect
          setNameState(saved);
        }
      }
    } catch {
      /* storage unavailable: keep the default */
    }
  }, []);

  const setName = useCallback((n: InstanceName) => {
    setNameState(n);
    try {
      window.localStorage.setItem(KEY, n);
    } catch {
      /* ignore */
    }
  }, []);

  const value = useMemo<InstanceState>(
    () => ({
      name,
      address: name === "demo" ? DEMO_ADDRESS : CANONICAL_ADDRESS,
      isDemo: name === "demo",
      setName,
      available,
    }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [name, setName],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useInstance(): InstanceState {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useInstance must be used inside InstanceProvider");
  return ctx;
}
