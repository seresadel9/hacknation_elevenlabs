"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { post } from "@/lib/api";
import { ConfirmDialog, ErrorState, Toast } from "@/components/ui";
import { useIntegrations } from "@/components/IntegrationsProvider";

function Constellation() {
  // Static, decorative: a dim map with a few lit nodes. No motion.
  const pts = [
    [120, 80, 1], [260, 140, 1], [400, 70, 0], [520, 170, 1], [660, 90, 0], [780, 200, 0], [880, 110, 0],
    [200, 250, 0], [360, 240, 1], [600, 280, 0], [960, 240, 0], [1080, 140, 0],
  ];
  const edges = [[0, 1], [1, 2], [1, 3], [3, 4], [4, 5], [5, 6], [1, 7], [7, 8], [8, 3], [3, 9], [6, 10], [6, 11]];
  return (
    <svg className="hero-art" viewBox="0 0 1200 320" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      <defs>
        <filter id="bloom" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="4" />
        </filter>
      </defs>
      {edges.map(([a, b], i) => {
        const lit = pts[a][2] && pts[b][2];
        return (
          <line key={i} x1={pts[a][0]} y1={pts[a][1]} x2={pts[b][0]} y2={pts[b][1]}
            stroke={lit ? "#4FE3FF" : "#ffffff"} strokeOpacity={lit ? 0.35 : 0.06} strokeWidth={1} />
        );
      })}
      {pts.map(([x, y, lit], i) => (
        <g key={i}>
          {lit ? <circle cx={x} cy={y} r={9} fill="#4FE3FF" opacity={0.5} filter="url(#bloom)" /> : null}
          <circle cx={x} cy={y} r={lit ? 4 : 3} fill={lit ? "#4FE3FF" : "none"} stroke={lit ? "none" : "#ffffff"}
            strokeOpacity={0.25} strokeDasharray={lit ? undefined : "2 2"} />
        </g>
      ))}
    </svg>
  );
}

export default function Home() {
  const router = useRouter();
  const { integrations } = useIntegrations();
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [confirmReset, setConfirmReset] = useState(false);

  async function trySample() {
    setBusy("sample");
    setError(null);
    try {
      const s = await post<{ id: string }>("/sessions", { mode: "lockin", use_demo_script: true, workflow_name: "" });
      router.push(`/capture/${s.id}`);
    } catch (e) {
      setError(e);
      setBusy(null);
    }
  }

  async function fastForward() {
    setBusy("ff");
    setError(null);
    try {
      const r = await post<{ lit: string[] }>("/demo/fast-forward");
      sessionStorage.setItem("umbra:lit", JSON.stringify(r.lit));
      router.push("/map");
    } catch (e) {
      setError(e);
      setBusy(null);
    }
  }

  async function reset() {
    setConfirmReset(false);
    try {
      await post("/demo/reset");
      setToast("Demo data cleared — the map is dark again.");
    } catch (e) {
      setError(e);
    }
  }

  return (
    <main id="main" className="container stack-lg">
      <section className="hero">
        <Constellation />
        <div className="stack" style={{ maxWidth: 760 }}>
          <span className="eyebrow">AI Apprentice · expert knowledge capture</span>
          <h1>
            Learn in the quiet.
            <br />
            <span style={{ color: "var(--accent)", textShadow: "0 0 30px rgba(79,227,255,.35)" }}>Master in the light.</span>
          </h1>
          <p className="tagline">
            Umbra watches how experienced people <em>actually</em> decide, holds every question until they&apos;re done,
            confirms what it learned with them — then turns it into a skill map new hires light up, one verified skill at a
            time.
          </p>
          <div className="row" style={{ marginTop: 10 }}>
            <button className="btn primary lg" onClick={trySample} disabled={!!busy}>
              {busy === "sample" ? "Preparing Mira's session…" : "Try sample workflow →"}
            </button>
            <button className="btn lg" onClick={fastForward} disabled={!!busy} title="Runs the full capture → debrief → confirm pipeline with Mira's seeded answers">
              {busy === "ff" ? "Lighting the map…" : "Skip to the lit map"}
            </button>
          </div>
          <p className="small faint">
            No setup, no API keys. The sample is a fictional Accounts Payable expert, &ldquo;Mira&rdquo;, processing five invoices.{" "}
            {integrations?.mode === "demo" && <span className="tag seed">Seeded demo data</span>}
          </p>
        </div>
      </section>

      {error ? <ErrorState error={error} onRetry={() => setError(null)} /> : null}

      <section aria-labelledby="stages-h" className="stack">
        <h2 id="stages-h" className="sr-only">
          Three stages
        </h2>
        <div className="grid-3">
          <Link href="/capture" className="card stage-card stack-sm" style={{ color: "inherit", textDecoration: "none" }}>
            <span className="stage-num">01 · CAPTURE</span>
            <h3>Observe quietly</h3>
            <p className="muted small">
              <strong style={{ color: "var(--text)" }}>Lock-In Mode</strong>: the expert works; Umbra stays silent and holds
              every question. When they finish, a focused debrief asks only what the screen couldn&apos;t reveal — why,
              thresholds, exceptions, never-dos, when to escalate.
            </p>
          </Link>
          <Link href="/map" className="card stage-card stack-sm" style={{ color: "inherit", textDecoration: "none" }}>
            <span className="stage-num">02 · MAP</span>
            <h3>Confirm, then it glows</h3>
            <p className="muted small">
              A teach-back in the apprentice&apos;s own words. The expert confirms, corrects or rejects. Only confirmed
              knowledge lights up in the graph — uncertain details stay visibly open.
            </p>
          </Link>
          <Link href="/illuminate" className="card stage-card stack-sm" style={{ color: "inherit", textDecoration: "none" }}>
            <span className="stage-num" style={{ color: "var(--violet)" }}>03 · ILLUMINATE</span>
            <h3>Light up the map</h3>
            <p className="muted small">
              New hires practise real decisions. A tutor grounded in the confirmed map steps in <em>before</em> a costly
              mistake and explains the expert&apos;s reasoning. Skills unlock on visible evidence, not points.
            </p>
          </Link>
        </div>
        <Link href="/trial" className="card amber row-between" style={{ color: "inherit", textDecoration: "none" }}>
          <div className="stack-sm">
            <span className="eyebrow amber">Separate path · Trial</span>
            <h3>Recruiting assessment — evidence, not a verdict</h3>
            <p className="muted small" style={{ maxWidth: 760 }}>
              Candidates work a new case against the same skill graph as a transparent rubric. No tutor, no hints, no
              answers leaked. Reviewers see the full path and per-skill evidence — never a single score or an automated
              hire/reject.
            </p>
          </div>
          <span className="btn">Open Trial →</span>
        </Link>
      </section>

      <section className="card stack-sm">
        <h4>What Umbra captures</h4>
        <p className="small muted">
          Timestamped events and the expert&apos;s own words — not raw recordings. Screen frames (when shared) are compared on
          your device to spot changes; with a vision model configured, an occasional frame is described in one sentence and
          discarded. Experts can pause, discard, or take any moment off the record at any time. Nothing is used for
          training until the expert confirms it.
        </p>
        <div className="row small">
          <button className="btn sm ghost" onClick={() => setConfirmReset(true)}>
            Reset demo data
          </button>
        </div>
      </section>

      <ConfirmDialog
        open={confirmReset}
        title="Reset all demo data?"
        body="This deletes every session, the Work Map, onboarding progress and Trial candidates in this local database."
        confirmLabel="Reset"
        danger
        onConfirm={reset}
        onCancel={() => setConfirmReset(false)}
      />
      <Toast message={toast} onDone={() => setToast(null)} />
    </main>
  );
}
