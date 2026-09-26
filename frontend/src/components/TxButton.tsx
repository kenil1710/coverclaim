"use client";

import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, Loader2, XCircle } from "lucide-react";
import { useState, type ReactNode } from "react";
import { waitForResult, type TransactionHash } from "@/lib/contract";
import type { WriteResult } from "@/types";
import { useWallet } from "./WalletProvider";

type State = "idle" | "signing" | "waiting" | "ok" | "rejected" | "error";

/**
 * A write from click to outcome. A REFUSAL IS NOT AN ERROR: CoverClaim never
 * raises, it returns {status: "REJECTED", reason} and credits any value back,
 * so the contract's own reason is shown verbatim and marked as a refusal.
 */
export function TxButton({
  label,
  pendingLabel = "Waiting for consensus…",
  icon,
  disabled,
  className = "btn btn-primary",
  send,
  onDone,
}: {
  label: string;
  pendingLabel?: string;
  icon?: ReactNode;
  disabled?: boolean;
  className?: string;
  send: (account: `0x${string}`) => Promise<TransactionHash>;
  onDone?: (result: WriteResult) => void;
}) {
  const { account, onRightNetwork, connect, switchNetwork } = useWallet();
  const [state, setState] = useState<State>("idle");
  const [message, setMessage] = useState("");

  async function run() {
    if (!account) {
      await connect();
      return;
    }
    if (!onRightNetwork) {
      await switchNetwork();
      return;
    }
    setState("signing");
    setMessage("");
    try {
      const hash = await send(account);
      setState("waiting");
      const result = await waitForResult(hash);
      if (result.status === "REJECTED") {
        setState("rejected");
        setMessage(String(result.reason ?? "The contract refused this call."));
      } else {
        setState("ok");
        setMessage("");
      }
      onDone?.(result);
    } catch (e) {
      const text = e instanceof Error ? e.message : String(e);
      setState("error");
      setMessage(/user rejected|denied/i.test(text) ? "Cancelled in the wallet." : text.slice(0, 220));
    }
  }

  const busy = state === "signing" || state === "waiting";
  return (
    <div style={{ display: "inline-flex", flexDirection: "column", gap: 8, maxWidth: "100%" }}>
      <button className={className} onClick={run} disabled={disabled || busy}>
        {busy ? <Loader2 size={16} className="spin" /> : state === "ok" ? <CheckCircle2 size={16} /> : icon}
        {busy ? (state === "signing" ? "Confirm in wallet…" : pendingLabel) : !account ? "Connect wallet" : !onRightNetwork ? "Switch to Studio Dev" : label}
      </button>
      <AnimatePresence>
        {message && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            role="status"
            style={{
              display: "flex",
              gap: 8,
              alignItems: "flex-start",
              maxWidth: 480,
              fontSize: "0.8rem",
              lineHeight: 1.5,
              color: state === "rejected" ? "var(--pending)" : "var(--excluded)",
              background: state === "rejected" ? "rgba(255,176,32,0.08)" : "rgba(255,77,94,0.08)",
              border: `1px solid ${state === "rejected" ? "rgba(255,176,32,0.25)" : "rgba(255,77,94,0.25)"}`,
              borderRadius: 10,
              padding: "9px 11px",
            }}
          >
            <XCircle size={14} style={{ flexShrink: 0, marginTop: 2 }} />
            <span className="break">
              {state === "rejected" && (
                <strong style={{ display: "block", marginBottom: 2 }}>Refused by the contract — nothing moved; anything sent is claimable.</strong>
              )}
              {message}
            </span>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
