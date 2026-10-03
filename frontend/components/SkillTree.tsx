"use client";

import Link from "next/link";
import type { LevelState } from "@/lib/types";

// Fixed constellation positions for the five onboarding skills (left → right = prerequisites → advanced).
const POS: Record<string, [number, number]> = {
  L1: [120, 170],
  L2: [400, 70],
  L3: [400, 270],
  L4: [620, 170],
  L5: [820, 170],
};

export function SkillTree({ levels, edges }: { levels: LevelState[]; edges: { src: string; dst: string }[] }) {
  const bySkill = new Map(levels.map((l) => [l.skill, l]));
  return (
    <svg viewBox="0 0 940 340" role="group" aria-label="Skill tree. Dark skills are not yet mastered; lit skills are mastered.">
      <defs>
        <filter id="tglow" x="-100%" y="-100%" width="300%" height="300%">
          <feGaussianBlur stdDeviation="9" />
        </filter>
      </defs>
      {edges.map((e, i) => {
        const a = bySkill.get(e.src);
        const b = bySkill.get(e.dst);
        if (!a || !b) return null;
        const [x1, y1] = POS[a.id];
        const [x2, y2] = POS[b.id];
        const lit = a.status === "mastered" && b.status === "mastered";
        const half = a.status === "mastered";
        return (
          <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke={lit ? "#4FE3FF" : half ? "#8B7CFF" : "#fff"}
            strokeOpacity={lit ? 0.6 : half ? 0.45 : 0.08} strokeWidth={lit ? 2 : 1.2} strokeDasharray={half && !lit ? "5 5" : undefined}
            style={{ transition: "stroke 1.4s, stroke-opacity 1.4s" }} />
        );
      })}
      {levels.map((l) => {
        const [x, y] = POS[l.id];
        const mastered = l.status === "mastered";
        const open = l.status === "available" || l.status === "practiced";
        return (
          <Link key={l.id} href={`/illuminate/${l.id}`} aria-label={`${l.title}: ${l.skill_title} — ${l.status.replace("_", " ")}`}>
            <g className="tree-node" transform={`translate(${x},${y})`} style={{ cursor: "pointer" }}>
              {mastered && <circle r={36} fill="#4FE3FF" opacity={0.45} filter="url(#tglow)" />}
              {open && <circle r={30} fill="#8B7CFF" opacity={0.25} filter="url(#tglow)" />}
              <circle className="orb" r={24} fill={mastered ? "#4FE3FF" : open ? "rgba(139,124,255,0.18)" : "#0c0d12"}
                stroke={mastered ? "#dff9ff" : open ? "#8B7CFF" : "rgba(255,255,255,0.25)"} strokeWidth={1.5}
                strokeDasharray={l.status === "awaiting_expert" ? "3 4" : undefined} />
              <text textAnchor="middle" y={5} fontSize={13} fill={mastered ? "#031015" : open ? "#d9d3ff" : "#6b7286"} fontFamily="var(--font-mono)">
                {mastered ? "✓" : l.status === "locked" || l.status === "awaiting_expert" ? "🔒︎" : l.id}
              </text>
              <text textAnchor="middle" y={48} fontSize={13} fill={mastered ? "#cfeff7" : open ? "#e6e9f2" : "#6b7286"}>{l.title}</text>
              <text textAnchor="middle" y={65} fontSize={11} fill="#6b7286">{l.subtitle}</text>
            </g>
          </Link>
        );
      })}
    </svg>
  );
}
