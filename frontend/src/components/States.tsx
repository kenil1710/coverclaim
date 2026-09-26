"use client";

import { AlertTriangle, Inbox, RefreshCw } from "lucide-react";
import type { ReactNode } from "react";

export function Skeleton({ h = 16, w = "100%", r = 10 }: { h?: number; w?: number | string; r?: number }) {
  return <div className="skeleton" style={{ height: h, width: w, borderRadius: r }} />;
}

export function CardSkeleton({ lines = 4 }: { lines?: number }) {
  return (
    <div className="card stack" aria-busy="true">
      <Skeleton h={20} w="45%" />
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton key={i} h={12} w={`${90 - i * 12}%`} />
      ))}
    </div>
  );
}

export function ErrorState({ title = "Could not load", message, retry }: { title?: string; message?: string; retry?: () => void }) {
  return (
    <div className="card row" style={{ borderColor: "rgba(255,77,94,0.3)", alignItems: "flex-start" }} role="alert">
      <AlertTriangle size={20} color="var(--excluded)" style={{ flexShrink: 0, marginTop: 2 }} />
      <div className="stack" style={{ gap: 6, flex: 1 }}>
        <strong>{title}</strong>
        <span className="muted" style={{ fontSize: "0.88rem" }}>
          {message ?? "Studio Dev did not answer. It is rate-limited and sometimes slow; this is not a contract failure."}
        </span>
        {retry && (
          <button className="btn btn-ghost btn-sm" onClick={retry} style={{ alignSelf: "flex-start" }}>
            <RefreshCw size={14} /> Retry
          </button>
        )}
      </div>
    </div>
  );
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="card stack" style={{ alignItems: "center", textAlign: "center", padding: 36 }}>
      <Inbox size={28} color="var(--dim)" />
      <strong>{title}</strong>
      {children && <div className="muted" style={{ fontSize: "0.88rem", maxWidth: 460 }}>{children}</div>}
    </div>
  );
}
