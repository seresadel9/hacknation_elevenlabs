import type { GraphEdge, GraphNode, NodeType } from "./types";

// Layered "observatory chart" layout: one horizontal band per node type, ordered by barycentre so related nodes
// sit near each other. Deterministic — the same graph always renders the same way.
const LAYER: Record<NodeType, number> = { step: 0, skill: 1, guardrail: 2, decision: 3, case: 4, evidence: 5 };

export interface Positioned {
  x: number;
  y: number;
}

export function layoutGraph(nodes: GraphNode[], edges: GraphEdge[], width = 1100, height = 660) {
  const layers: GraphNode[][] = [[], [], [], [], [], []];
  for (const n of nodes) layers[LAYER[n.type]].push(n);
  layers.forEach((l) => l.sort((a, b) => a.key.localeCompare(b.key)));
  const used = layers.filter((l) => l.length > 0);
  const neighbours = new Map<string, string[]>();
  for (const e of edges) {
    neighbours.set(e.src, [...(neighbours.get(e.src) ?? []), e.dst]);
    neighbours.set(e.dst, [...(neighbours.get(e.dst) ?? []), e.src]);
  }
  const pos = new Map<string, Positioned>();
  const top = 60;
  const bandH = used.length > 1 ? (height - top - 70) / (used.length - 1) : 0;
  const place = () =>
    used.forEach((layer, li) => {
      const gap = width / (layer.length + 1);
      layer.forEach((n, i) => pos.set(n.key, { x: gap * (i + 1), y: top + li * bandH + (layer.length > 7 ? (i % 2 ? 16 : -16) : 0) }));
    });
  place();
  for (let iter = 0; iter < 8; iter++) {
    for (const layer of used) {
      const bary = new Map<string, number>();
      for (const n of layer) {
        const xs = (neighbours.get(n.key) ?? []).map((k) => pos.get(k)?.x).filter((x): x is number => x !== undefined);
        bary.set(n.key, xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : (pos.get(n.key)?.x ?? 0));
      }
      layer.sort((a, b) => (bary.get(a.key) ?? 0) - (bary.get(b.key) ?? 0));
    }
    place();
  }
  return pos;
}

export function truncate(s: string, n: number) {
  return s.length > n ? s.slice(0, n - 1) + "…" : s;
}
