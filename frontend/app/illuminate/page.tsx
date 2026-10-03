"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { api, post } from "@/lib/api";
import type { LevelState } from "@/lib/types";
import { SkillTree } from "@/components/SkillTree";
import { ConfirmDialog, EmptyState, ErrorState, Loading, Toast } from "@/components/ui";

interface Overview {
  levels: LevelState[];
  rubric: { id: string; label: string }[];
  tree: { nodes: unknown[]; edges: { src: string; dst: string }[] };
  map_ready: boolean;
  mastered: number;
}

const STATUS_TEXT: Record<string, string> = {
  mastered: "Mastered",
  available: "Ready",
  practiced: "In progress",
  locked: "Locked",
  awaiting_expert: "Awaiting expert",
};

export default function IlluminatePage() {
  const [ov, setOv] = useState<Overview | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [confirmReset, setConfirmReset] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const load = useCallback(() => {
    api<Overview>("/illuminate").then((o) => { setOv(o); setError(null); }).catch(setError);
  }, []);
  useEffect(load, [load]);

  async function fastForward() {
    setBusy(true);
    try {
      await post("/demo/fast-forward");
      load();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  if (error) return <main id="main" className="container"><ErrorState error={error} onRetry={load} /></main>;
  if (!ov) return <main id="main" className="container"><Loading label="Loading your skill map" /></main>;

  return (
    <main id="main" className="container stack-lg" data-mode="illuminate">
      <div className="row-between">
        <div className="stack-sm">
          <span className="eyebrow violet">03 · Illuminate · onboarding</span>
          <h1>Light up the map</h1>
          <p className="muted" style={{ maxWidth: 680 }}>
            Every skill here comes from Mira&apos;s expert-confirmed Work Map. Predict what you&apos;d do, get coached, and
            light each skill once the evidence says you&apos;ve got it.
          </p>
        </div>
        <div className="stack-sm" style={{ alignItems: "flex-end" }}>
          <span className="mono" style={{ fontSize: 28 }}>{ov.mastered}<span className="faint">/{ov.levels.length}</span></span>
          <span className="small muted">skills lit</span>
        </div>
      </div>

      {!ov.map_ready && (
        <EmptyState icon="◌" title="Nothing to learn yet — the expert hasn't confirmed anything">
          <p className="muted small" style={{ maxWidth: 560 }}>
            Illuminate only teaches expert-confirmed knowledge. Capture and confirm a session first, or load Mira&apos;s
            sample — it runs the same capture → debrief → confirm pipeline with her seeded answers.
          </p>
          <div className="row" style={{ justifyContent: "center" }}>
            <Link href="/capture" className="btn">Capture a session</Link>
            <button className="btn violet" onClick={fastForward} disabled={busy}>{busy ? "Lighting…" : "Load the confirmed sample map"}</button>
          </div>
        </EmptyState>
      )}

      <div className="skilltree-wrap">
        <SkillTree levels={ov.levels} edges={ov.tree.edges} />
      </div>

      <div className="split">
        <section className="stack" aria-labelledby="levels-h">
          <h2 id="levels-h">Missions</h2>
          {ov.levels.map((l) => {
            const open = l.status !== "locked" && l.status !== "awaiting_expert";
            return (
              <div key={l.id} className={`card level-card ${l.status === "mastered" ? "glow" : open ? "violet" : ""}`}>
                <span className={`level-orb ${l.status}`} aria-hidden="true">{l.status === "mastered" ? "✓" : l.id}</span>
                <div className="stack-sm">
                  <div className="row" style={{ gap: 8 }}>
                    <h3>{l.title}</h3>
                    <span className="muted small">· {l.subtitle}</span>
                    <span className={`tag ${l.status === "mastered" ? "accent" : open ? "violet" : ""}`}>{STATUS_TEXT[l.status]}</span>
                  </div>
                  <p className="small muted">{l.goal}</p>
                  {l.lock_reasons.map((r) => (
                    <p key={r} className="tiny faint">🔒︎ {r}</p>
                  ))}
                </div>
                {open ? (
                  <Link href={`/illuminate/${l.id}`} className={`btn ${l.status === "mastered" ? "" : "violet"}`}>
                    {l.status === "mastered" ? "Replay" : l.status === "practiced" ? "Continue" : "Start"}
                  </Link>
                ) : (
                  <Link href={`/illuminate/${l.id}`} className="btn ghost">Why locked?</Link>
                )}
              </div>
            );
          })}
        </section>
        <aside className="stack">
          <div className="card stack-sm">
            <h4>Mastery rubric — the same for every skill</h4>
            {ov.rubric.map((r) => (
              <div key={r.id} className="rubric-line"><span className="mark">·</span>{r.label}</div>
            ))}
            <p className="tiny faint">
              No points, no streaks. A skill lights up only when your stored attempts meet every line — and you can always
              see which attempts those were.
            </p>
          </div>
          <div className="card tight stack-sm small muted">
            <span>Locks only ever show what you need first — never the answers.</span>
            <button className="btn sm ghost" onClick={() => setConfirmReset(true)} style={{ alignSelf: "flex-start" }}>Reset my progress</button>
          </div>
        </aside>
      </div>
      <ConfirmDialog open={confirmReset} title="Reset onboarding progress?" body="Deletes your attempts and mastery evidence. The expert's Work Map is untouched." confirmLabel="Reset" danger
        onConfirm={async () => { setConfirmReset(false); await post("/illuminate/reset"); setToast("Progress reset — the tree is dark again."); load(); }}
        onCancel={() => setConfirmReset(false)} />
      <Toast message={toast} onDone={() => setToast(null)} />
    </main>
  );
}
