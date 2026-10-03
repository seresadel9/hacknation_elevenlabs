"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, post } from "@/lib/api";
import { ErrorState } from "@/components/ui";
import { useIntegrations } from "@/components/IntegrationsProvider";

const SAMPLE = "Supplier invoice processing — Mira, Accounts Payable";

interface SessionSummary {
  id: string;
  workflow_name: string;
  mode: "lockin" | "live";
  status: string;
  seeded: boolean;
  created_at: string;
}

export default function CaptureSetup() {
  const router = useRouter();
  const { integrations } = useIntegrations();
  const [name, setName] = useState(SAMPLE);
  const [mode, setMode] = useState<"lockin" | "live">("lockin");
  const [useSample, setUseSample] = useState(true);
  const [share, setShare] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [sessions, setSessions] = useState<SessionSummary[] | null>(null);

  useEffect(() => {
    api<SessionSummary[]>("/sessions").then(setSessions).catch(() => setSessions([]));
  }, []);

  async function create() {
    setBusy(true);
    setError(null);
    try {
      const s = await post<{ id: string }>("/sessions", {
        workflow_name: name,
        mode,
        use_demo_script: useSample,
        screen_share: share,
      });
      router.push(`/capture/${s.id}`);
    } catch (e) {
      setError(e);
      setBusy(false);
    }
  }

  const vision = integrations?.vision.configured;

  return (
    <main id="main" className="container stack-lg">
      <div className="stack-sm">
        <span className="eyebrow">01 · Capture</span>
        <h1>Start a workflow-learning session</h1>
        <p className="muted" style={{ maxWidth: 720 }}>
          You work as usual. Umbra observes, keeps timestamped notes, and learns what it can&apos;t see by asking you —
          on your terms.
        </p>
      </div>

      <div className="split-wide">
        <div className="stack">
          <div className="card stack">
            <label className="field">
              Task or workflow name
              <input type="text" value={name} onChange={(e) => setName(e.target.value)} maxLength={120} />
            </label>

            <fieldset className="stack-sm" style={{ border: 0, padding: 0, margin: 0 }}>
              <legend className="small muted" style={{ marginBottom: 8 }}>
                How should Umbra ask its questions?
              </legend>
              <div className="grid-2">
                <button type="button" role="radio" aria-checked={mode === "lockin"} className="choice" onClick={() => setMode("lockin")}>
                  <span className="radio" aria-hidden="true" />
                  <span className="stack-sm">
                    <strong>Lock-In Mode</strong>
                    <span className="small muted">
                      Total quiet. No questions spoken or shown while you work — they&apos;re held until you end, then asked
                      one at a time in a short debrief.
                    </span>
                    <span className="tag accent" style={{ alignSelf: "flex-start" }}>Signature · recommended for focus work</span>
                  </span>
                </button>
                <button type="button" role="radio" aria-checked={mode === "live"} className="choice" onClick={() => setMode("live")}>
                  <span className="radio" aria-hidden="true" />
                  <span className="stack-sm">
                    <strong>Live Coaching</strong>
                    <span className="small muted">
                      Brief questions only at natural pauses, only about what&apos;s on screen — never while you type, read or
                      speak. At most ~1 every 2 minutes.
                    </span>
                  </span>
                </button>
              </div>
            </fieldset>

            <div className="stack-sm">
              <label className="row small" style={{ cursor: "pointer" }}>
                <input type="checkbox" checked={useSample} onChange={(e) => setUseSample(e.target.checked)} />
                <span>
                  Play the seeded sample session <span className="tag sim">Simulated</span>{" "}
                  <span className="muted">— Mira handles 5 fictional invoices (recommended without a vision model)</span>
                </span>
              </label>
              <label className="row small" style={{ cursor: "pointer" }}>
                <input type="checkbox" checked={share} onChange={(e) => setShare(e.target.checked)} />
                <span>
                  Offer screen sharing{" "}
                  <span className="muted">
                    — {vision ? "frames are described by the vision model, then discarded" : "change detection runs on your device only; no vision model configured"}
                  </span>
                </span>
              </label>
            </div>
            {error ? <ErrorState error={error} /> : null}
            <div className="row">
              <button className="btn primary lg" onClick={create} disabled={busy || !name.trim()}>
                {busy ? "Preparing…" : "Review & continue →"}
              </button>
              <span className="small faint">Nothing is observed until you press Start on the next screen.</span>
            </div>
          </div>
        </div>

        <aside className="stack">
          <div className="card stack-sm">
            <h4>What will be observed and stored</h4>
            <ul className="small muted stack-sm" style={{ paddingLeft: 18, margin: 0 }}>
              <li>
                <strong style={{ color: "var(--text)" }}>Stored:</strong> timestamped work events (e.g. &ldquo;changed GL 6400 → 0720&rdquo;),
                notes you type or say, and your debrief answers.
              </li>
              <li>
                <strong style={{ color: "var(--text)" }}>Not stored:</strong> video, screenshots or raw audio. Shared-screen frames
                are compared locally to detect changes{vision ? "; an occasional frame is described by the vision model and discarded" : ""}.
              </li>
              <li>
                <strong style={{ color: "var(--text)" }}>Your controls, always visible:</strong> pause, off the record, strike any moment, end, discard.
              </li>
              <li>
                <strong style={{ color: "var(--text)" }}>Where it goes:</strong> this app&apos;s local SQLite database. Nothing reaches the Work
                Map or training until you confirm it.
              </li>
              {integrations?.elevenlabs.configured && (
                <li>
                  <strong style={{ color: "var(--text)" }}>Voice:</strong> if you choose to speak, audio streams to ElevenLabs for
                  transcription; only the text is kept.
                </li>
              )}
            </ul>
          </div>
          {sessions && sessions.length > 0 && (
            <div className="card stack-sm">
              <h4>Recent sessions</h4>
              <ul className="stack-sm" style={{ listStyle: "none", padding: 0, margin: 0 }}>
                {sessions.slice(0, 6).map((s) => (
                  <li key={s.id} className="row-between small">
                    <Link href={["debrief", "review", "committed"].includes(s.status) ? `/capture/${s.id}/debrief` : `/capture/${s.id}`}>
                      {s.workflow_name.slice(0, 44)}
                    </Link>
                    <span className="row" style={{ gap: 6 }}>
                      <span className="tag">{s.mode === "lockin" ? "Lock-In" : "Live"}</span>
                      <span className="tag">{s.status}</span>
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </aside>
      </div>
    </main>
  );
}
