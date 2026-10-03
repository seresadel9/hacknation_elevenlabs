"use client";

import { useEffect, useRef } from "react";
import { ApiError } from "@/lib/api";
import type { NodeStatus, Provenance } from "@/lib/types";

export const STATUS_LABEL: Record<NodeStatus, string> = {
  draft: "Draft",
  needs_confirmation: "Needs confirmation",
  confirmed: "Expert-confirmed",
};

export function StatusBadge({ status }: { status: NodeStatus }) {
  return (
    <span className={`status ${status}`}>
      <span className="dot" aria-hidden="true" />
      {STATUS_LABEL[status]}
    </span>
  );
}

export function ProvenanceTag({ p, confirmed, by }: { p: Provenance; confirmed?: boolean; by?: string | null }) {
  if (p === "expert_statement") return <span className="tag expert">Expert said</span>;
  if (p === "observed") return <span className="tag observed">Observed</span>;
  return (
    <span className="tag inference" title="Umbra's own restatement — never a direct quote.">
      AI inference{by === "llm" || by === "model" ? " · model" : ""}
      {confirmed ? " · confirmed" : ""}
    </span>
  );
}

export function SourceTag({ source }: { source: string }) {
  if (source === "simulated") return <span className="tag sim" title="Seeded demo observation standing in for a vision model">Simulated</span>;
  if (source === "expert") return <span className="tag expert">Expert</span>;
  if (source === "vision") return <span className="tag model">Vision model</span>;
  if (source === "system") return <span className="tag">System</span>;
  return <span className="tag observed">Observed</span>;
}

export function Loading({ label = "Loading" }: { label?: string }) {
  return (
    <div className="stack" aria-busy="true" aria-live="polite">
      <span className="sr-only">{label}…</span>
      <div className="skeleton" style={{ height: 28, width: "40%" }} />
      <div className="skeleton" style={{ height: 140 }} />
      <div className="skeleton" style={{ height: 90 }} />
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const e = error instanceof ApiError ? error : null;
  const offline = e?.kind === "offline";
  const notFound = e?.status === 404;
  return (
    <div className="card state error" role="alert">
      <div className="icon">{offline ? "⌁" : notFound ? "?" : "!"}</div>
      <h3>{offline ? "Can't reach Umbra" : notFound ? "Not found" : "Something went wrong"}</h3>
      <p className="muted small" style={{ maxWidth: 520 }}>
        {offline
          ? "The backend isn't responding. Start it (see README) — nothing you've confirmed is lost; it's stored in SQLite."
          : e?.message || String(error)}
      </p>
      {onRetry && (
        <button className="btn" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}

export function EmptyState({
  icon = "○",
  title,
  children,
}: {
  icon?: string;
  title: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="card state">
      <div className="icon" aria-hidden="true">
        {icon}
      </div>
      <h3>{title}</h3>
      {children}
    </div>
  );
}

export function ConfirmDialog({
  open,
  title,
  body,
  confirmLabel,
  danger,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  body: React.ReactNode;
  confirmLabel: string;
  danger?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) d.showModal();
    if (!open && d.open) d.close();
  }, [open]);
  return (
    <dialog ref={ref} className="modal" onCancel={onCancel} aria-labelledby="dlg-title">
      <div className="stack">
        <h3 id="dlg-title">{title}</h3>
        <div className="muted small">{body}</div>
        <div className="row" style={{ justifyContent: "flex-end" }}>
          <button className="btn ghost" onClick={onCancel}>
            Cancel
          </button>
          <button className={`btn ${danger ? "danger" : "primary"}`} onClick={onConfirm} autoFocus>
            {confirmLabel}
          </button>
        </div>
      </div>
    </dialog>
  );
}

export function Toast({ message, onDone }: { message: string | null; onDone: () => void }) {
  useEffect(() => {
    if (!message) return;
    const t = window.setTimeout(onDone, 3200);
    return () => window.clearTimeout(t);
  }, [message, onDone]);
  if (!message) return null;
  return (
    <div className="toast" role="status">
      {message}
    </div>
  );
}

export const GAP_LABEL: Record<string, string> = {
  why: "Why",
  change_condition: "What would change it",
  threshold: "Threshold",
  exception: "Exception",
  never: "Never-do",
  escalation: "Escalation",
  contradiction: "Contradiction",
};

export function eur(n: number) {
  return "€" + n.toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
