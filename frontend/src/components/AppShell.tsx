"use client";

import { AnimatePresence, motion } from "framer-motion";
import { FlaskConical, Menu, ShieldCheck, Wallet, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { useInstance } from "@/lib/instance";
import { short } from "@/lib/format";
import { Wordmark } from "./Logo";
import { useWallet } from "./WalletProvider";
import { Footer } from "./Footer";

const NAV = [
  { href: "/pools", label: "Pools" },
  { href: "/claim", label: "File claim" },
  { href: "/claims", label: "Claims" },
  { href: "/underwriter", label: "Underwriter" },
  { href: "/docs", label: "Docs" },
];

function InstanceSwitch() {
  const { name, setName, available } = useInstance();
  if (available.length < 2) return null;
  return (
    <div className="pill" style={{ padding: 3, gap: 2 }} role="tablist" aria-label="Contract instance">
      {available.map((n) => (
        <button
          key={n}
          role="tab"
          aria-selected={name === n}
          onClick={() => setName(n)}
          style={{
            border: 0,
            cursor: "pointer",
            borderRadius: 999,
            padding: "3px 10px",
            fontSize: "0.72rem",
            fontWeight: 700,
            letterSpacing: "0.06em",
            background: name === n ? (n === "demo" ? "var(--pending)" : "var(--orange)") : "transparent",
            color: name === n ? "#120a05" : "var(--muted)",
          }}
        >
          {n === "demo" ? "DEMO" : "CANONICAL"}
        </button>
      ))}
    </div>
  );
}

function WalletButton() {
  const { account, onRightNetwork, hasWallet, connect, switchNetwork, connecting, error } = useWallet();
  const asked = useRef(false);
  // Auto network switch: once per session, when a connected wallet is on the
  // wrong chain. Never on the landing page (no wallet UI there at all).
  useEffect(() => {
    if (account && !onRightNetwork && !asked.current) {
      asked.current = true;
      void switchNetwork();
    }
  }, [account, onRightNetwork, switchNetwork]);
  if (!hasWallet) {
    return (
      <a className="btn btn-ghost btn-sm" href="https://metamask.io" target="_blank" rel="noreferrer">
        <Wallet size={14} /> Get a wallet
      </a>
    );
  }
  if (!account) {
    return (
      <button className="btn btn-primary btn-sm" onClick={() => void connect()} disabled={connecting} title={error ?? undefined}>
        <Wallet size={14} /> {connecting ? "Connecting…" : "Connect"}
      </button>
    );
  }
  if (!onRightNetwork) {
    return (
      <button className="btn btn-ghost btn-sm" onClick={() => void switchNetwork()} style={{ borderColor: "var(--pending)", color: "var(--pending)" }}>
        Switch network
      </button>
    );
  }
  return (
    <span className="pill" style={{ color: "var(--ink)" }}>
      <span style={{ width: 7, height: 7, borderRadius: 99, background: "var(--covered)" }} />
      {short(account)}
    </span>
  );
}

export function DemoBanner() {
  const { isDemo } = useInstance();
  if (!isDemo) return null;
  return (
    <div style={{ background: "rgba(255,176,32,0.08)", borderBottom: "1px solid rgba(255,176,32,0.22)", position: "relative", zIndex: 2 }}>
      <div className="wrap row" style={{ padding: "7px 16px", fontSize: "0.78rem", color: "var(--pending)", gap: 8, flexWrap: "nowrap", alignItems: "flex-start" }}>
        <FlaskConical size={14} style={{ flexShrink: 0, marginTop: 3 }} />
        <span className="break">
          <strong>DEMO instance.</strong> Every cover here starts 1,521 days before it is bought (fixed at deployment) so real 2022–2023 hacks can be replayed. Not insurance. Switch to CANONICAL for strict backdating.
        </span>
      </div>
    </div>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const path = usePathname();
  // Open for ONE path: navigating closes it without an effect.
  const [openAt, setOpenAt] = useState<string | null>(null);
  const open = openAt === path;
  const setOpen = (f: (o: boolean) => boolean) => setOpenAt(f(open) ? path : null);
  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <header style={{ position: "sticky", top: 0, zIndex: 20, background: "rgba(11,11,15,0.82)", backdropFilter: "blur(14px)", borderBottom: "1px solid var(--line)" }}>
        <div className="wrap row between" style={{ height: 62, flexWrap: "nowrap" }}>
          <Link href="/" aria-label="CoverClaim home">
            <Wordmark size={28} />
          </Link>
          <nav className="row hide-sm" style={{ gap: 4, flexWrap: "nowrap" }}>
            {NAV.map((n) => {
              const active =
                path === n.href ||
                (n.href === "/pools" && path.startsWith("/pool/")) ||
                (n.href === "/claims" && path.startsWith("/claim/"));
              return (
                <Link
                  key={n.href}
                  href={n.href}
                  style={{
                    padding: "7px 12px",
                    borderRadius: 999,
                    fontSize: "0.88rem",
                    fontWeight: 500,
                    color: active ? "var(--ink)" : "var(--muted)",
                    background: active ? "rgba(255,107,44,0.12)" : "transparent",
                  }}
                >
                  {n.label}
                </Link>
              );
            })}
          </nav>
          <div className="row" style={{ gap: 8, flexWrap: "nowrap" }}>
            <span className="pill hide-sm" title="GenLayer Studio Dev, chain 61997">
              <ShieldCheck size={12} color="var(--orange)" /> Studio Dev
            </span>
            <div className="hide-sm">
              <InstanceSwitch />
            </div>
            <WalletButton />
            <button className="btn btn-ghost btn-sm show-sm" aria-label="Menu" onClick={() => setOpen((o) => !o)} style={{ padding: 8 }}>
              {open ? <X size={16} /> : <Menu size={16} />}
            </button>
          </div>
        </div>
        <AnimatePresence>
          {open && (
            <motion.nav
              className="show-sm"
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              style={{ overflow: "hidden", borderTop: "1px solid var(--line)" }}
            >
              <div className="wrap stack" style={{ padding: "12px 16px", gap: 4 }}>
                {NAV.map((n) => (
                  <Link key={n.href} href={n.href} style={{ padding: "10px 4px", borderBottom: "1px solid var(--line)" }}>
                    {n.label}
                  </Link>
                ))}
                <div className="row" style={{ paddingTop: 10 }}>
                  <span className="pill"><ShieldCheck size={12} color="var(--orange)" /> Studio Dev</span>
                  <InstanceSwitch />
                </div>
              </div>
            </motion.nav>
          )}
        </AnimatePresence>
      </header>
      <DemoBanner />
      <motion.main
        key={path}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, ease: [0.2, 0.8, 0.2, 1] }}
        style={{ flex: 1, position: "relative", zIndex: 1 }}
      >
        {children}
      </motion.main>
      <Footer />
    </div>
  );
}

export function PageHead({ eyebrow, title, children, right }: { eyebrow: string; title: ReactNode; children?: ReactNode; right?: ReactNode }) {
  return (
    <div className="row between" style={{ padding: "36px 0 22px", alignItems: "flex-end", gap: 16 }}>
      <div className="stack" style={{ gap: 8, maxWidth: 720 }}>
        <span className="eyebrow">{eyebrow}</span>
        <h2>{title}</h2>
        {children && <p className="muted">{children}</p>}
      </div>
      {right}
    </div>
  );
}
