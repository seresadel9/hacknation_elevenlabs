"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError, post } from "@/lib/api";
import type { SessionEvent, SessionState } from "@/lib/types";
import { useScreenShare } from "@/lib/useScreenShare";
import { ConfirmDialog, ErrorState, Loading, SourceTag, Toast } from "@/components/ui";
import { useIntegrations } from "@/components/IntegrationsProvider";
import { VoiceNarration } from "@/components/VoiceNarration";

export default function SessionWorkspace() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { integrations } = useIntegrations();
  const [s, setS] = useState<SessionState | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState("");
  const [liveAnswer, setLiveAnswer] = useState("");
  const [confirmDiscard, setConfirmDiscard] = useState(false);
  const [confirmEnd, setConfirmEnd] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [speaking, setSpeaking] = useState(false);
  const pollRef = useRef<number | null>(null);

  const load = useCallback(async () => {
    try {
      const st = await api<SessionState>(`/sessions/${id}`);
      setS(st);
      setError(null);
      if (["debrief", "review", "committed"].includes(st.status)) router.replace(`/capture/${id}/debrief`);
    } catch (e) {
      setError(e);
    }
  }, [id, router]);

  useEffect(() => {
    load();
  }, [load]);

  const running = s?.status === "active";
  useEffect(() => {
    if (!running) return;
    pollRef.current = window.setInterval(load, 1000);
    return () => {
      if (pollRef.current) window.clearInterval(pollRef.current);
    };
  }, [running, load]);

  const share = useScreenShare(id, {
    active: !!running && !s?.off_record,
    vision: !!integrations?.vision.configured,
    speaking,
  });

  async function act(fn: () => Promise<SessionState | unknown>, msg?: string) {
    setBusy(true);
    try {
      const r = await fn();
      if (r && typeof r === "object" && "id" in (r as SessionState)) setS(r as SessionState);
      if (msg) setToast(msg);
    } catch (e) {
      setToast(e instanceof ApiError ? e.message : "Action failed");
    } finally {
      setBusy(false);
    }
  }

  const control = (action: string) => act(() => post<SessionState>(`/sessions/${id}/control`, { action }));

  async function end() {
    setConfirmEnd(false);
    setBusy(true);
    try {
      share.stop();
      await post(`/sessions/${id}/control`, { action: "end" });
      router.push(`/capture/${id}/debrief`);
    } catch (e) {
      setToast(e instanceof ApiError ? e.message : "Could not end the session");
      setBusy(false);
    }
  }

  async function discard() {
    setConfirmDiscard(false);
    share.stop();
    try {
      await api(`/sessions/${id}`, { method: "DELETE" });
      router.push("/capture");
    } catch (e) {
      setToast(e instanceof ApiError ? e.message : "Could not discard");
    }
  }

  if (error && !s) return <main id="main" className="container"><ErrorState error={error} onRetry={load} /></main>;
  if (!s) return <main id="main" className="container"><Loading label="Loading session" /></main>;

  const lockin = s.mode === "lockin";
  const statusLabel =
    s.status === "ready" ? "Ready — not observing yet"
    : s.off_record ? "Off the record — nothing is captured"
    : s.status === "paused" ? "Paused — nothing is observed"
    : lockin ? "Observing quietly"
    : "Observing · questions only at natural pauses";

  return (
    <main id="main" className="container stack-lg">
      {/* ------------------------------------------------ top bar */}
      <div className="row-between">
        <div className="stack-sm">
          <div className="row" style={{ gap: 8 }}>
            <span className="eyebrow">01 · Capture</span>
            <span className="tag">{lockin ? "Lock-In Mode" : "Live Coaching"}</span>
            {s.seeded && <span className="tag sim">Simulated observations</span>}
            {s.seeded && <span className="tag seed">Demo clock ×{s.speed}</span>}
          </div>
          <h2>{s.workflow_name}</h2>
        </div>
        <div className="row" aria-live="polite">
          {share.state === "sharing" && (
            <span className="pill sharing">
              <span className="rec-dot" aria-hidden="true" /> Sharing screen
            </span>
          )}
          <span className="pill">
            <span className={`breath ${s.off_record ? "off" : s.status === "active" ? "on" : "paused"}`} aria-hidden="true" />
            {statusLabel}
          </span>
          <span className="pill mono" aria-label={`Session clock ${s.clock}`}>
            {s.clock}
          </span>
        </div>
      </div>

      {/* ------------------------------------------------ ready: explain before starting */}
      {s.status === "ready" && (
        <div className="card glow stack">
          <h3>Before you start</h3>
          <div className="grid-2 small muted">
            <div className="stack-sm">
              <p>
                {lockin ? (
                  <>
                    <strong style={{ color: "var(--text)" }}>Lock-In Mode.</strong> Umbra will not speak, ask, or show any
                    question while you work. You&apos;ll only see a count of questions it is holding. When you end, it asks
                    them one at a time.
                  </>
                ) : (
                  <>
                    <strong style={{ color: "var(--text)" }}>Live Coaching.</strong> Umbra may ask a brief question at a
                    natural pause, about what&apos;s on screen. It never interrupts typing, reading, speaking or navigation.
                  </>
                )}
              </p>
              <p>
                Captured: timestamped work events, your notes{integrations?.elevenlabs.scribe_realtime ? " and narration (as text)" : ""}.
                Not captured: video, screenshots or raw audio.
              </p>
            </div>
            <div className="stack-sm">
              <p>
                You can <strong style={{ color: "var(--text)" }}>pause</strong>, go{" "}
                <strong style={{ color: "var(--text)" }}>off the record</strong>, strike any moment, or{" "}
                <strong style={{ color: "var(--text)" }}>discard</strong> everything at any time.
              </p>
              {s.seeded && (
                <p>
                  This sample replays a fictional ten-minute session (Mira, Accounts Payable) at ×{s.speed} speed, standing
                  in for screen understanding. Use <span className="kbd">Next moment</span> to skip ahead.
                </p>
              )}
            </div>
          </div>
          <div className="row">
            <button className="btn primary lg" onClick={() => control("start")} disabled={busy}>
              Start observing
            </button>
            {s.screen_share && share.state !== "sharing" && (
              <button className="btn" onClick={share.start}>
                Share screen…
              </button>
            )}
            <button className="btn ghost" onClick={() => setConfirmDiscard(true)}>
              Discard
            </button>
          </div>
          <ShareStatus state={share.state} vision={!!integrations?.vision.configured} />
        </div>
      )}

      {s.status !== "ready" && (
        <div className="split">
          <div className="stack">
            {/* ------------------------------------------------ the quiet stage */}
            {lockin ? (
              <section className="quiet-stage" aria-label="Lock-In status">
                <div>
                  <div className={`quiet-ring ${s.status === "active" && !s.off_record ? "on" : ""}`}>
                    <span className="held-count" aria-label={`${s.held_question_count} questions held`}>
                      {s.held_question_count}
                    </span>
                  </div>
                  <p style={{ fontFamily: "var(--font-ui)", fontSize: 18 }}>
                    {s.held_question_count === 1 ? "question held" : "questions held"} for the debrief
                  </p>
                  <p className="small muted" style={{ maxWidth: 420, margin: "8px auto 0" }}>
                    Nothing will be asked — or shown — until you end the session. Asked so far:{" "}
                    <strong style={{ color: "var(--text)" }}>{s.questions_asked_during_session}</strong>.
                  </p>
                  {s.seeded && s.script_complete && s.status === "active" && (
                    <p className="small" style={{ marginTop: 14, color: "var(--accent)" }}>
                      The sample session is complete — end it to begin the debrief.
                    </p>
                  )}
                </div>
              </section>
            ) : (
              <LiveCoachingPanel
                s={s}
                answer={liveAnswer}
                setAnswer={setLiveAnswer}
                busy={busy}
                onAnswer={(defer) =>
                  act(async () => {
                    const r = await post<SessionState>(`/sessions/${id}/live-answer`, {
                      question_id: s.live_question!.id,
                      answer: defer ? null : liveAnswer,
                      defer,
                    });
                    setLiveAnswer("");
                    return r;
                  }, defer ? "Saved for the debrief." : "Answer captured as your own words.")
                }
              />
            )}

            {/* ------------------------------------------------ controls */}
            <div className="card tight row" role="toolbar" aria-label="Session controls">
              {s.status === "active" ? (
                <button className="btn" onClick={() => control("pause")} disabled={busy}>
                  ❚❚ Pause
                </button>
              ) : (
                <button className="btn" onClick={() => control("resume")} disabled={busy}>
                  ▶ Resume
                </button>
              )}
              <button
                className={`btn ${s.off_record ? "danger" : ""}`}
                aria-pressed={s.off_record}
                onClick={() => act(() => post<SessionState>(`/sessions/${id}/off-record`, { on: !s.off_record }))}
                disabled={busy}
              >
                {s.off_record ? "● Back on the record" : "Off the record"}
              </button>
              {s.seeded && (
                <button className="btn" onClick={() => control("advance")} disabled={busy || s.status !== "active" || s.script_complete}>
                  Next moment ⏭
                </button>
              )}
              {s.screen_share && share.state !== "sharing" && (
                <button className="btn" onClick={share.start}>
                  Share screen…
                </button>
              )}
              {share.state === "sharing" && (
                <button className="btn" onClick={share.stop}>
                  Stop sharing
                </button>
              )}
              <span style={{ flex: 1 }} />
              <button className="btn ghost" onClick={() => setConfirmDiscard(true)}>
                Discard
              </button>
              <button className="btn primary" onClick={() => setConfirmEnd(true)} disabled={busy}>
                End session → debrief
              </button>
            </div>
            <ShareStatus state={share.state} vision={!!integrations?.vision.configured} />

            {/* ------------------------------------------------ notes */}
            <form
              className="card tight stack-sm"
              onSubmit={(e) => {
                e.preventDefault();
                if (!note.trim()) return;
                act(async () => {
                  const r = await post<SessionState>(`/sessions/${id}/notes`, { text: note });
                  setNote("");
                  return r;
                }, "Noted — in your own words.");
              }}
            >
              <label className="field" htmlFor="note">
                Say it in your own words (optional) — reasons you note here won&apos;t be asked again
              </label>
              <div className="row" style={{ flexWrap: "nowrap" }}>
                <input
                  id="note"
                  type="text"
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder={s.off_record ? "Off the record — nothing is captured" : "e.g. “Anything over €5k net per item goes to capex”"}
                  disabled={s.off_record || s.status !== "active"}
                  maxLength={1000}
                />
                <button className="btn" disabled={!note.trim() || s.off_record || s.status !== "active"}>
                  Add note
                </button>
              </div>
              {integrations?.elevenlabs.scribe_realtime && (
                <VoiceNarration sessionId={id} disabled={s.off_record || s.status !== "active"} onSpeaking={setSpeaking} onCommitted={load} />
              )}
            </form>
          </div>

          {/* ------------------------------------------------ event log */}
          <aside className={`card stack-sm ${lockin ? "dim-log" : ""}`} aria-label="What Umbra has noted">
            <div className="row-between">
              <h4>What Umbra has noted</h4>
              <span className="tiny faint">{s.events.filter((e) => e.kind !== "marker").length} moments</span>
            </div>
            <p className="tiny faint">
              Timestamped events only — no recordings. Strike anything to take it off the record; questions that depended on
              it are dropped.
            </p>
            <EventLog events={s.events} onStrike={(e) => act(() => post<SessionState>(`/sessions/${id}/events/${e.id}/strike`), "Removed from the record.")} />
          </aside>
        </div>
      )}

      <ConfirmDialog
        open={confirmEnd}
        title="End the session?"
        body={
          lockin
            ? `Observation stops and the debrief begins. Umbra is holding ${s.held_question_count} question(s); it will ask the most important ones, one at a time.`
            : "Observation stops and the debrief begins with anything still open."
        }
        confirmLabel="End & start debrief"
        onConfirm={end}
        onCancel={() => setConfirmEnd(false)}
      />
      <ConfirmDialog
        open={confirmDiscard}
        title="Discard this session?"
        body="Every captured event, note and held question is permanently deleted. Nothing reaches the Work Map."
        confirmLabel="Discard everything"
        danger
        onConfirm={discard}
        onCancel={() => setConfirmDiscard(false)}
      />
      <Toast message={toast} onDone={() => setToast(null)} />
      <p className="small faint">
        <Link href="/capture">← All sessions</Link>
      </p>
    </main>
  );
}

function ShareStatus({ state, vision }: { state: string; vision: boolean }) {
  if (state === "denied")
    return (
      <div className="card tight danger small" role="alert">
        Screen sharing was blocked. That&apos;s fine — Umbra keeps working from your notes
        {""} and the sample observations. You can allow it from your browser&apos;s address bar and try again.
      </div>
    );
  if (state === "unsupported")
    return (
      <div className="card tight small muted" role="status">
        This browser can&apos;t share a screen here. Umbra continues with notes and (in the demo) simulated observations.
      </div>
    );
  if (state === "ended")
    return (
      <div className="card tight small muted" role="status">
        Screen sharing stopped. Observation continues from notes.
      </div>
    );
  if (state === "sharing")
    return (
      <p className="tiny faint">
        Screen changes are detected on your device{vision ? "; an occasional frame is described by the vision model and discarded" : " — no vision model is configured, so frames never leave this browser"}.
      </p>
    );
  return null;
}

function LiveCoachingPanel({
  s,
  answer,
  setAnswer,
  busy,
  onAnswer,
}: {
  s: SessionState;
  answer: string;
  setAnswer: (v: string) => void;
  busy: boolean;
  onAnswer: (defer: boolean) => void;
}) {
  const q = s.live_question;
  return (
    <section className="stack" aria-live="polite">
      {q ? (
        <div className="card glow question-card stack">
          <div className="row" style={{ gap: 8 }}>
            <span className="eyebrow">Natural pause · about what&apos;s on screen</span>
            {q.simulated && <span className="tag sim">Simulated</span>}
          </div>
          <p className="question-text">{q.text}</p>
          <textarea value={answer} onChange={(e) => setAnswer(e.target.value)} placeholder="A sentence or two is plenty." aria-label="Your answer" />
          <div className="row">
            <button className="btn primary" disabled={busy || !answer.trim()} onClick={() => onAnswer(false)}>
              Answer
            </button>
            <button className="btn" disabled={busy} onClick={() => onAnswer(true)}>
              Later — ask in the debrief
            </button>
            {q.sample_answer && (
              <button className="btn ghost" onClick={() => setAnswer(q.sample_answer!)}>
                Use Mira&apos;s answer <span className="tag seed">Seeded</span>
              </button>
            )}
          </div>
        </div>
      ) : (
        <div className="quiet-stage" style={{ minHeight: 200 }}>
          <div>
            <p style={{ fontFamily: "var(--font-ui)", fontSize: 18 }}>Watching for a natural pause</p>
            <p className="small muted" style={{ maxWidth: 440, margin: "6px auto 0" }}>
              Questions appear only when you stop — never while you type, read, speak or navigate. Held for later:{" "}
              <strong style={{ color: "var(--text)" }}>{s.held_question_count}</strong>.
            </p>
          </div>
        </div>
      )}
      {s.pacing_log.length > 0 && (
        <details className="card tight small">
          <summary className="muted" style={{ cursor: "pointer" }}>
            Pacing log — why Umbra did or didn&apos;t ask ({s.pacing_log.filter((p) => p.decision === "asked").length} asked)
          </summary>
          <ul className="stack-sm" style={{ listStyle: "none", padding: 0, marginTop: 10 }}>
            {s.pacing_log.map((p, i) => (
              <li key={i} className="row" style={{ alignItems: "baseline", flexWrap: "nowrap" }}>
                <span className="mono faint">{p.clock}</span>
                <span className={`tag ${p.decision === "asked" ? "accent" : ""}`}>{p.decision}</span>
                <span className="muted">{p.reason}</span>
              </li>
            ))}
          </ul>
        </details>
      )}
      {s.live_answered.length > 0 && (
        <div className="card tight stack-sm small">
          <h4>Answered at pauses</h4>
          {s.live_answered.map((a) => (
            <div key={a.id} className="stack-sm">
              <span className="muted">{a.text}</span>
              {a.answer ? <span className="quote">{a.answer}</span> : <span className="faint">Deferred to the debrief</span>}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function EventLog({ events, onStrike }: { events: SessionEvent[]; onStrike: (e: SessionEvent) => void }) {
  const endRef = useRef<HTMLLIElement>(null);
  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "nearest" });
  }, [events.length]);
  if (events.length === 0) return <p className="small faint">Nothing yet.</p>;
  return (
    <ol className="event-log">
      {events.map((e) => (
        <li key={e.id} className={`${e.kind === "marker" ? "marker" : ""} ${e.off_record ? "struck" : ""} ${e.kind === "pause" ? "pause" : ""}`}>
          <span className="clock">{e.clock}</span>
          <span className="stack-sm" style={{ gap: 4 }}>
            <span className="txt">{e.kind === "note" || e.kind === "transcript" ? <span className="quote">{e.text}</span> : e.text}</span>
            {e.kind !== "marker" && !e.off_record && (
              <span className="row" style={{ gap: 6 }}>
                <SourceTag source={e.source} />
                {e.case && <span className="tag">{e.case}</span>}
              </span>
            )}
          </span>
          {e.kind !== "marker" && !e.off_record ? (
            <button className="btn ghost sm" onClick={() => onStrike(e)} aria-label={`Take “${e.text.slice(0, 40)}” off the record`} title="Take off the record">
              ✕
            </button>
          ) : (
            <span />
          )}
        </li>
      ))}
      <li ref={endRef} aria-hidden="true" style={{ border: 0, padding: 0 }} />
    </ol>
  );
}
