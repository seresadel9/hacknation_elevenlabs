"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { api, post } from "@/lib/api";
import type { Graph, GraphNode, NodeType } from "@/lib/types";
import { GraphLegend, GraphView } from "@/components/GraphView";
import { SkillCard } from "@/components/SkillCard";
import { EmptyState, ErrorState, Loading, StatusBadge } from "@/components/ui";

const TYPES: { id: NodeType; label: string }[] = [
  { id: "skill", label: "Skills" },
  { id: "guardrail", label: "Guardrails" },
  { id: "step", label: "Workflow steps" },
  { id: "decision", label: "Decisions" },
  { id: "case", label: "Cases" },
  { id: "evidence", label: "Evidence" },
];

export default function MapPage() {
  const [graph, setGraph] = useState<Graph | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [view, setView] = useState<"graph" | "list">("graph");
  const [selected, setSelected] = useState<string | null>(null);
  const [detail, setDetail] = useState<GraphNode | null>(null);
  const [lit, setLit] = useState<string[]>([]);
  const [hidden, setHidden] = useState<Set<NodeType>>(new Set());
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    api<Graph>("/graph").then((g) => { setGraph(g); setError(null); }).catch(setError);
  }, []);

  useEffect(() => {
    try {
      const raw = sessionStorage.getItem("umbra:lit");
      if (raw) {
        setLit(JSON.parse(raw));
        sessionStorage.removeItem("umbra:lit");
      }
    } catch {}
    if (window.matchMedia("(max-width: 720px)").matches) setView("list");
    const hash = decodeURIComponent(window.location.hash.slice(1));
    if (hash) setSelected(hash);
    load();
  }, [load]);

  useEffect(() => {
    if (!selected) return;
    api<GraphNode>(`/graph/nodes/${encodeURIComponent(selected)}`).then(setDetail).catch(() => setDetail(null));
    history.replaceState(null, "", `#${selected}`);
  }, [selected, graph]);

  const nodes = useMemo(() => (graph?.nodes ?? []).filter((n) => !hidden.has(n.type)), [graph, hidden]);
  const keys = useMemo(() => new Set(nodes.map((n) => n.key)), [nodes]);
  const edges = useMemo(() => (graph?.edges ?? []).filter((e) => keys.has(e.src) && keys.has(e.dst)), [graph, keys]);

  async function fastForward() {
    setBusy(true);
    try {
      const r = await post<{ lit: string[] }>("/demo/fast-forward");
      setLit(r.lit);
      load();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  if (error) return <main id="main" className="container"><ErrorState error={error} onRetry={load} /></main>;
  if (!graph) return <main id="main" className="container"><Loading label="Loading the Work Map" /></main>;

  if (graph.nodes.length === 0)
    return (
      <main id="main" className="container stack-lg">
        <div className="stack-sm">
          <span className="eyebrow">02 · Map</span>
          <h1>Work Map</h1>
        </div>
        <EmptyState icon="◌" title="The map is still dark">
          <p className="muted small" style={{ maxWidth: 520 }}>
            Nothing has been captured yet. Run a session and the nodes Umbra observes will appear here dim — they light up
            only once the expert confirms them.
          </p>
          <div className="row" style={{ justifyContent: "center" }}>
            <Link href="/capture" className="btn primary">Capture a session</Link>
            <button className="btn" onClick={fastForward} disabled={busy}>
              {busy ? "Running the sample pipeline…" : "Load Mira's confirmed sample map"}
            </button>
          </div>
        </EmptyState>
      </main>
    );

  const c = graph.counts;
  return (
    <main id="main" className="container stack" style={{ maxWidth: 1440 }}>
      <div className="row-between">
        <div className="stack-sm">
          <span className="eyebrow">02 · Map</span>
          <h1 style={{ fontSize: 30 }}>Work Map</h1>
        </div>
        <div className="row small" aria-label="Review status counts">
          <StatusBadge status="draft" /> <span className="mono">{c.draft}</span>
          <StatusBadge status="needs_confirmation" /> <span className="mono">{c.needs_confirmation}</span>
          <StatusBadge status="confirmed" /> <span className="mono">{c.confirmed}</span>
        </div>
      </div>

      {lit.length > 0 && (
        <div className="card glow tight small row" role="status">
          <span className="breath on" aria-hidden="true" />
          {lit.length} nodes just moved into the light — confirmed by the expert. Uncertain details stay open on their cards.
          <Link href="/illuminate" style={{ marginLeft: "auto" }}>Continue to Illuminate →</Link>
        </div>
      )}

      <div className="row-between">
        <div className="tabs" role="tablist" aria-label="View">
          <button role="tab" aria-selected={view === "graph"} onClick={() => setView("graph")}>Graph</button>
          <button role="tab" aria-selected={view === "list"} onClick={() => setView("list")}>List / tree</button>
        </div>
        <div className="row" role="group" aria-label="Filter node types" style={{ gap: 6 }}>
          {TYPES.map((t) => (
            <button
              key={t.id}
              className={`btn sm ${hidden.has(t.id) ? "ghost" : ""}`}
              aria-pressed={!hidden.has(t.id)}
              onClick={() => setHidden((h) => { const n = new Set(h); if (n.has(t.id)) n.delete(t.id); else n.add(t.id); return n; })}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      <div className="split-wide">
        <div className="stack-sm">
          {view === "graph" ? (
            <>
              <div className="graph-wrap">
                <GraphView nodes={nodes} edges={edges} selected={selected} onSelect={setSelected} lit={lit} />
              </div>
              <GraphLegend />
              <p className="tiny faint">Dashed edges: constrained by a guardrail · amber: exception to · arrows: prerequisite for. Every node is clickable and keyboard-focusable.</p>
            </>
          ) : (
            <ListView nodes={nodes} graph={graph} selected={selected} onSelect={setSelected} />
          )}
        </div>
        <aside className="card card-scroll sticky" aria-live="polite">
          {detail ? (
            <SkillCard node={detail} onSelect={setSelected} />
          ) : (
            <div className="state">
              <div className="icon">◇</div>
              <p className="muted small">Select a node to see its skill card — evidence, thresholds, guardrails and review status.</p>
            </div>
          )}
        </aside>
      </div>
    </main>
  );
}

function ListView({ nodes, graph, selected, onSelect }: { nodes: GraphNode[]; graph: Graph; selected: string | null; onSelect: (k: string) => void }) {
  const children = (key: string) =>
    graph.edges
      .filter((e) => e.src === key && ["constrained_by", "demonstrated_by"].includes(e.type))
      .map((e) => graph.nodes.find((n) => n.key === e.dst))
      .filter((n): n is GraphNode => !!n && nodes.includes(n));
  const row = (n: GraphNode, depth = 0) => (
    <button className="node-row" aria-current={selected === n.key} onClick={() => onSelect(n.key)} style={{ paddingLeft: 10 + depth * 22 }}>
      <StatusBadge status={n.status} />
      <span style={{ flex: 1 }}>{n.title}</span>
      <span className="tag">{n.type}</span>
    </button>
  );
  return (
    <div className="card stack">
      {TYPES.map((t) => {
        const group = nodes.filter((n) => n.type === t.id);
        if (!group.length) return null;
        return (
          <section key={t.id} className="stack-sm">
            <h4>{t.label}</h4>
            <ul className="tree-list" role="tree" aria-label={t.label}>
              {group.map((n) => (
                <li key={n.key} role="treeitem" aria-selected={selected === n.key}>
                  {row(n)}
                  {t.id === "skill" && (
                    <ul className="tree-list" role="group">
                      {children(n.key).map((ch) => (
                        <li key={ch.key} role="treeitem" aria-selected={selected === ch.key}>{row(ch, 1)}</li>
                      ))}
                    </ul>
                  )}
                </li>
              ))}
            </ul>
          </section>
        );
      })}
    </div>
  );
}
