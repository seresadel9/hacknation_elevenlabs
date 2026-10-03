"use client";

import { useEffect, useMemo, useState } from "react";
import { layoutGraph, truncate } from "@/lib/layout";
import type { GraphEdge, GraphNode, NodeStatus } from "@/lib/types";
import { STATUS_LABEL } from "./ui";

const W = 1100;
const H = 660;

function Shape({ type, status }: { type: GraphNode["type"]; status: NodeStatus }) {
  const lit = status === "confirmed";
  const pending = status === "needs_confirmation";
  const fill = lit ? "#4FE3FF" : pending ? "rgba(139,124,255,0.22)" : "#0A0B0F";
  const stroke = lit ? "#bff6ff" : pending ? "#8B7CFF" : "rgba(255,255,255,0.32)";
  const dash = status === "draft" ? "3 3" : undefined;
  const common = { className: "shape", fill, stroke, strokeWidth: 1.4, strokeDasharray: dash };
  switch (type) {
    case "skill":
      return <circle r={14} {...common} />;
    case "guardrail":
      return <rect x={-10} y={-10} width={20} height={20} transform="rotate(45)" {...common} />;
    case "step":
      return <rect x={-9} y={-9} width={18} height={18} rx={4} {...common} />;
    case "case":
      return <rect x={-7} y={-7} width={14} height={14} {...common} />;
    case "evidence":
      return <circle r={4.5} {...common} />;
    default:
      return <circle r={8} {...common} />;
  }
}

export function GraphView({
  nodes,
  edges,
  selected,
  onSelect,
  lit,
}: {
  nodes: GraphNode[];
  edges: GraphEdge[];
  selected: string | null;
  onSelect: (key: string) => void;
  lit: string[];
}) {
  const pos = useMemo(() => layoutGraph(nodes, edges, W, H), [nodes, edges]);
  const litSet = useMemo(() => new Set(lit), [lit]);
  // Signature beat: freshly confirmed nodes render dim first, then ignite one after another.
  const [revealed, setRevealed] = useState(lit.length === 0);
  useEffect(() => {
    if (!lit.length) return;
    const t = window.setTimeout(() => setRevealed(true), 500);
    return () => window.clearTimeout(t);
  }, [lit]);
  const order = useMemo(() => new Map(lit.map((k, i) => [k, i])), [lit]);
  const status = (n: GraphNode): NodeStatus => (!revealed && litSet.has(n.key) ? "draft" : n.status);
  const byKey = useMemo(() => new Map(nodes.map((n) => [n.key, n])), [nodes]);
  const hover = selected;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="group" aria-label="Work Map knowledge graph. Use Tab to move between nodes and Enter to inspect.">
      <defs>
        <filter id="glow" x="-100%" y="-100%" width="300%" height="300%">
          <feGaussianBlur stdDeviation="6" />
        </filter>
        <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
          <path d="M0,0 L10,5 L0,10 z" fill="rgba(255,255,255,0.25)" />
        </marker>
      </defs>
      {edges.map((e) => {
        const a = pos.get(e.src);
        const b = pos.get(e.dst);
        const na = byKey.get(e.src);
        const nb = byKey.get(e.dst);
        if (!a || !b || !na || !nb) return null;
        const bothLit = status(na) === "confirmed" && status(nb) === "confirmed";
        const touching = hover && (e.src === hover || e.dst === hover);
        const mx = (a.x + b.x) / 2 + (a.y === b.y ? 0 : (b.x - a.x) * 0.08);
        const my = (a.y + b.y) / 2 - (a.y === b.y ? 34 : 0);
        const dash = e.type === "constrained_by" ? "4 4" : e.type === "exception_to" ? "2 5" : undefined;
        return (
          <path
            key={e.id}
            className="g-edge"
            d={`M${a.x},${a.y} Q${mx},${my} ${b.x},${b.y}`}
            fill="none"
            stroke={e.type === "exception_to" ? "#FFB547" : bothLit ? "#4FE3FF" : "#ffffff"}
            strokeOpacity={touching ? 0.85 : bothLit ? 0.32 : e.type === "exception_to" ? 0.35 : 0.07}
            strokeWidth={touching ? 1.6 : 1}
            strokeDasharray={dash}
            markerEnd={e.type === "prerequisite_for" ? "url(#arrow)" : undefined}
            style={{ transitionDelay: `${(order.get(e.dst) ?? 0) * 70}ms` }}
          >
            <title>{`${na.title} — ${e.type.replace(/_/g, " ")} → ${nb.title}`}</title>
          </path>
        );
      })}
      {nodes.map((n) => {
        const p = pos.get(n.key);
        if (!p) return null;
        const st = status(n);
        const isSel = selected === n.key;
        const showLabel = n.type !== "evidence" || isSel;
        const delay = `${(order.get(n.key) ?? 0) * 70}ms`;
        return (
          <g
            key={n.key}
            className={`g-node ${st} ${isSel ? "selected" : ""}`}
            transform={`translate(${p.x},${p.y})`}
            tabIndex={0}
            role="button"
            aria-pressed={isSel}
            aria-label={`${n.type} · ${n.title} · ${STATUS_LABEL[n.status]}`}
            onClick={() => onSelect(n.key)}
            onKeyDown={(ev) => {
              if (ev.key === "Enter" || ev.key === " ") {
                ev.preventDefault();
                onSelect(n.key);
              }
            }}
          >
            <title>{`${n.title} · ${STATUS_LABEL[n.status]}`}</title>
            {/* generous hit area so small nodes stay easy to click */}
            <circle r={18} fill="transparent" />
            {st === "confirmed" && (
              <circle className="shape" r={n.type === "skill" ? 20 : n.type === "evidence" ? 8 : 14} fill="#4FE3FF" opacity={0.45} filter="url(#glow)" style={{ transitionDelay: delay }} />
            )}
            <g style={{ transitionDelay: delay }}>
              <Shape type={n.type} status={st} />
            </g>
            <circle className="focus-ring" r={n.type === "skill" ? 20 : 15} fill="none" stroke="transparent" strokeWidth={1.2} />
            {showLabel && (
              <text className="label" y={n.type === "skill" ? 32 : 24} textAnchor="middle">
                {truncate(n.title, n.type === "skill" ? 30 : 24)}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
}

export function GraphLegend() {
  return (
    <div className="legend" aria-label="Legend">
      <span><svg width="14" height="14"><circle cx="7" cy="7" r="6" fill="#4FE3FF" /></svg>Skill</span>
      <span><svg width="14" height="14"><rect x="3" y="3" width="8" height="8" transform="rotate(45 7 7)" fill="#4FE3FF" /></svg>Guardrail</span>
      <span><svg width="14" height="14"><circle cx="7" cy="7" r="4" fill="#4FE3FF" /></svg>Decision</span>
      <span><svg width="14" height="14"><rect x="2" y="2" width="10" height="10" rx="2" fill="#4FE3FF" /></svg>Workflow step</span>
      <span><svg width="14" height="14"><rect x="3" y="3" width="8" height="8" fill="#4FE3FF" /></svg>Case</span>
      <span><svg width="14" height="14"><circle cx="7" cy="7" r="2.5" fill="#4FE3FF" /></svg>Evidence</span>
      <span style={{ marginLeft: 8 }}><svg width="14" height="14"><circle cx="7" cy="7" r="5" fill="none" stroke="rgba(255,255,255,.4)" strokeDasharray="2 2" /></svg>Draft</span>
      <span><svg width="14" height="14"><circle cx="7" cy="7" r="5" fill="rgba(139,124,255,.25)" stroke="#8B7CFF" /></svg>Needs confirmation</span>
      <span><svg width="14" height="14"><circle cx="7" cy="7" r="5" fill="#4FE3FF" /></svg>Expert-confirmed</span>
    </div>
  );
}
