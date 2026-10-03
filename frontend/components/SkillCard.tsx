"use client";

import Link from "next/link";
import type { CardItem, GraphNode } from "@/lib/types";
import { ProvenanceTag, StatusBadge } from "./ui";

const TYPE_LABEL: Record<string, string> = {
  skill: "Skill",
  decision: "Decision",
  guardrail: "Guardrail",
  step: "Workflow step",
  case: "Case / scenario",
  evidence: "Evidence · source moment",
};

const REL_LABEL: Record<string, [string, string]> = {
  prerequisite_for: ["Prerequisite for", "Requires"],
  depends_on: ["Depends on", "Needed by"],
  demonstrated_by: ["Demonstrated by", "Demonstrates"],
  constrained_by: ["Constrained by", "Constrains"],
  exception_to: ["Exception to", "Has exception"],
  supported_by_evidence: ["Supported by evidence", "Evidence for"],
};

function Items({ title, items, hint }: { title: string; items: CardItem[]; hint?: string }) {
  if (!items?.length) return null;
  return (
    <section className="field-block">
      <h4>{title}</h4>
      {hint && <span className="tiny faint">{hint}</span>}
      <ul>
        {items.map((it, i) => (
          <li key={i} className="stack-sm" style={{ gap: 4 }}>
            {it.provenance === "expert_statement" && it.quote ? (
              <>
                <span className="quote">{it.quote}</span>
                {it.text !== it.quote && <span className="small muted inference">{it.text}</span>}
              </>
            ) : (
              <span className={it.provenance === "ai_inference" ? "inference" : ""}>{it.text}</span>
            )}
            <span className="row" style={{ gap: 6 }}>
              <ProvenanceTag p={it.provenance} confirmed={it.confirmed} by={it.paraphrase_by} />
              {it.provenance === "expert_statement" && it.quote && it.text !== it.quote && (
                <span className="tag inference" title="The line under the quote is Umbra's restatement">+ AI restatement</span>
              )}
              {it.sources?.filter((s) => s.clock).slice(0, 2).map((s, j) => (
                <span key={j} className="tag mono">{s.clock}</span>
              ))}
              {it.via && <span className="tiny faint">via {it.via}</span>}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function SkillCard({ node, onSelect, compact }: { node: GraphNode; onSelect?: (key: string) => void; compact?: boolean }) {
  const c = node.card;
  return (
    <article className="stack" aria-labelledby={`card-${node.key}`}>
      <div className="stack-sm">
        <div className="row-between">
          <span className="eyebrow">{TYPE_LABEL[node.type]}</span>
          <StatusBadge status={node.status} />
        </div>
        <h2 id={`card-${node.key}`} style={{ fontSize: 20 }}>{node.title}</h2>
        {node.summary && <p className="muted small">{node.summary}</p>}
        <div className="row" style={{ gap: 6 }}>
          {node.seeded && <span className="tag seed">Seeded demo</span>}
          <span className="tag mono">{node.key}</span>
        </div>
      </div>

      {node.status !== "confirmed" && (
        <div className="unresolved small">
          {node.status === "draft"
            ? "Draft — inferred from observation only. Not used for training until the expert confirms it."
            : "Needs confirmation — the expert hasn't confirmed this yet. Not used for training."}
        </div>
      )}

      {c.meaning && (
        <section className="field-block">
          <h4>What it means</h4>
          <span className="inference">{c.meaning.text}</span>
          <span><ProvenanceTag p={c.meaning.provenance} confirmed={c.meaning.confirmed} /></span>
        </section>
      )}
      {c.when && (
        <section className="field-block">
          <h4>When it applies</h4>
          <span className="inference">{c.when.text}</span>
        </section>
      )}
      <Items title="Thresholds" items={c.thresholds} />
      <Items title="Never" items={c.never} />
      <Items title="Escalate / stop and ask" items={c.escalation} />
      <Items title="Exceptions" items={c.exceptions} />
      <Items title="Why the expert decides this way" items={c.why} />
      <Items title="How to perform it" items={c.how} />
      <Items title="What Umbra saw" items={c.observations} />

      {c.open_questions?.length > 0 && (
        <section className="field-block">
          <h4>Open questions · not confirmed</h4>
          <ul>
            {c.open_questions.map((q, i) => (
              <li key={i} className="unresolved">
                {q.text}
                <div className="tiny faint">{q.reason}</div>
              </li>
            ))}
          </ul>
        </section>
      )}

      {!compact && c.evidence?.length > 0 && (
        <section className="field-block">
          <h4>Evidence · source moments</h4>
          <ul>
            {c.evidence.map((e, i) => (
              <li key={i} className="row small" style={{ alignItems: "baseline", flexWrap: "nowrap" }}>
                {e.clock && <span className="mono faint">{e.clock}</span>}
                <span className={e.kind === "expert_statement" ? "quote" : "muted"}>{e.text}</span>
                {e.kind === "expert_statement" ? <span className="tag expert">Expert said</span> : e.simulated ? <span className="tag sim">Simulated</span> : <span className="tag observed">Observed</span>}
              </li>
            ))}
          </ul>
        </section>
      )}

      {!compact && node.relations && node.relations.length > 0 && (
        <section className="field-block">
          <h4>Relationships</h4>
          <ul>
            {node.relations.map((r, i) => (
              <li key={i} className="row small" style={{ flexWrap: "nowrap" }}>
                <span className="faint" style={{ minWidth: 150 }}>{REL_LABEL[r.type]?.[r.direction === "out" ? 0 : 1] ?? r.type}</span>
                {onSelect ? (
                  <button className="btn sm ghost" style={{ justifyContent: "flex-start", whiteSpace: "normal", textAlign: "left" }} onClick={() => onSelect(r.node.key)}>
                    {r.node.title}
                  </button>
                ) : (
                  <Link href={`/map#${r.node.key}`}>{r.node.title}</Link>
                )}
                <StatusBadge status={r.node.status} />
              </li>
            ))}
          </ul>
        </section>
      )}
    </article>
  );
}
