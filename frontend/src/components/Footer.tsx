import Link from "next/link";
import { Wordmark } from "./Logo";
import { CANONICAL_ADDRESS, DEMO_ADDRESS, REGISTRY_ADDRESS } from "@/lib/genlayer";

export function Footer() {
  return (
    <footer style={{ borderTop: "1px solid var(--line)", marginTop: 48, position: "relative", zIndex: 1 }}>
      <div className="wrap grid g3" style={{ padding: "32px 16px", gap: 24 }}>
        <div className="stack" style={{ gap: 10 }}>
          <Wordmark size={24} />
          <p className="muted" style={{ fontSize: "0.84rem", maxWidth: 320 }}>
            DeFi hack cover where claims are judged by GenLayer validators against frozen policy wording — not by a vote of the people who pay.
          </p>
        </div>
        <div className="stack" style={{ gap: 6, fontSize: "0.84rem" }}>
          <strong style={{ fontSize: "0.8rem", color: "var(--muted)" }}>PRODUCT</strong>
          <Link href="/pools">Pools</Link>
          <Link href="/claim">File a claim</Link>
          <Link href="/claims">Claims</Link>
          <Link href="/underwriter">Underwrite</Link>
          <Link href="/docs">Docs</Link>
        </div>
        <div className="stack" style={{ gap: 6, fontSize: "0.78rem" }}>
          <strong style={{ fontSize: "0.8rem", color: "var(--muted)" }}>CONTRACTS · STUDIO DEV 61997</strong>
          {DEMO_ADDRESS && <span className="mono break dim">Demo {DEMO_ADDRESS}</span>}
          {CANONICAL_ADDRESS && <span className="mono break dim">Canonical {CANONICAL_ADDRESS}</span>}
          {REGISTRY_ADDRESS && <span className="mono break dim">Registry {REGISTRY_ADDRESS}</span>}
          <a className="dim" href="https://github.com/kenil1710/coverclaim" target="_blank" rel="noreferrer">github.com/kenil1710/coverclaim</a>
        </div>
      </div>
    </footer>
  );
}
