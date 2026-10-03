"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { api, ApiError, post } from "@/lib/api";
import type { Debrief, TeachItem, Teachback } from "@/lib/types";
import { ErrorState, GAP_LABEL, Loading, ProvenanceTag, SourceTag, Toast } from "@/components/ui";
import { AgentPanel, MicButton, SpeakButton } from "@/components/VoiceTools";

export default function DebriefPage() {
  const { id } = useParams<{ id: string }>();
  const [d, setD] = useState<Debrief | null>(null);
  const [tb, setTb] = useState<Teachback | null>(null);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(async () => {
    try {
      const deb = await api<Debrief>(`/sessions/${id}/debrief`);
      setD(deb);
      if (deb.session.status !== "debrief") setTb(await api<Teachback>(`/sessions/${id}/teachback`));
      setError(null);
    } catch (e) {
      setError(e);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  if (error) {
    const early = error instanceof ApiError && error.status === 409;
    return (
      <main id="main" className="container stack">
        <ErrorState error={error} onRetry={load} />
        {early && (
          <p className="center">
            <Link href={`/capture/${id}`} className="btn">
              ← Back to the running session
            </Link>
          </p>
        )}
      </main>
    );
  }
  if (!d) return <main id="main" className="container"><Loading label="Opening debrief" /></main>;

  return (
    <main id="main" className="container stack-lg">
      <div className="stack-sm">
        <div className="row" style={{ gap: 8 }}>
          <span className="eyebrow">01 · Capture → debrief</span>
          <span className="tag">{d.session.mode === "lockin" ? "Lock-In Mode" : "Live Coaching"}</span>
          {d.session.seeded && <span className="tag sim">Simulated session</span>}
        </div>
        <h1 style={{ fontSize: 32 }}>{d.session.status === "debrief" ? "Debrief" : "Teach-back"}</h1>
        <p className="muted">{d.session.workflow_name}</p>
      </div>
      {d.session.status === "debrief" ? <DebriefFlow d={d} setD={setD} onFinished={(t) => setTb(t)} id={id} /> : tb ? <TeachbackView tb={tb} setTb={setTb} id={id} /> : <Loading />}
    </main>
  );
}

/* ================================================================================================ debrief */

function DebriefFlow({ d, setD, onFinished, id }: { d: Debrief; setD: (d: Debrief) => void; onFinished: (t: Teachback) => void; id: string }) {
  const [answer, setAnswer] = useState("");
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const q = d.current;
  const lockin = d.session.mode === "lockin";
  const pct = d.progress.target ? Math.min(100, (d.progress.asked / d.progress.target) * 100) : 100;

  async function send(skip: boolean) {
    if (!q) return;
    setBusy(true);
    try {
      setD(await post<Debrief>(`/sessions/${id}/debrief/answer`, { question_id: q.id, answer: skip ? null : answer, skip }));
      setAnswer("");
    } catch (e) {
      setToast(e instanceof ApiError ? e.message : "Couldn't save the answer");
    } finally {
      setBusy(false);
    }
  }

  async function finish() {
    setBusy(true);
    try {
      onFinished(await post<Teachback>(`/sessions/${id}/debrief/finish`));
      window.scrollTo({ top: 0 });
      // Re-fetch the debrief so the page switches to the teach-back.
      setD(await api<Debrief>(`/sessions/${id}/debrief`));
    } catch (e) {
      setToast(e instanceof ApiError ? e.message : "Couldn't finish the debrief");
      setBusy(false);
    }
  }

  const agentContext =
    "You are Umbra, a respectful apprentice debriefing an expert after a work session. Ask ONE question at a time, " +
    "exactly as written, then listen. Current question: " + (q?.text ?? "none — thank the expert.");

  return (
    <div className="split">
      <div className="stack">
        {lockin ? (
          <div className="card glow row" role="status" style={{ flexWrap: "nowrap" }}>
            <span className="breath" aria-hidden="true" />
            <span>
              <strong>Umbra asked you {d.questions_asked_during_session} questions during the session.</strong>{" "}
              <span className="muted">
                It held {d.held_during_session} quietly while you worked; here are the ones that matter most, one at a time.
              </span>
            </span>
          </div>
        ) : (
          <div className="card tight small muted" role="status">
            {d.questions_asked_during_session} question(s) were asked live at natural pauses. These are the ones still open.
          </div>
        )}

        {q ? (
          <section className="card question-card stack" aria-live="polite" aria-labelledby="q-text">
            <div className="row-between">
              <div className="row" style={{ gap: 6 }}>
                <span className="eyebrow">
                  Question {d.progress.asked + 1}
                  {d.progress.asked < d.progress.target ? ` of ${d.progress.target}` : " · optional"}
                </span>
                {q.gap_types.map((g) => (
                  <span key={g} className="tag">{GAP_LABEL[g] ?? g}</span>
                ))}
                <span className={`tag ${q.generator === "model" ? "model" : "seed"}`} title="How this question was produced">
                  {q.generator === "model" ? "Model-generated" : "Evidence-based rules · demo fallback"}
                </span>
              </div>
              <SpeakButton text={q.text} autoPlay />
            </div>
            <div className="progress" aria-hidden="true"><span style={{ width: `${pct}%` }} /></div>
            {q.evidence && (
              <div className="evidence-anchor">
                <span className="clock">{q.evidence.clock}</span>
                <span className="muted">{q.evidence.text}</span>
                <SourceTag source={q.evidence.source} />
              </div>
            )}
            <p id="q-text" className="question-text">{q.text}</p>
            <label className="sr-only" htmlFor="answer">Your answer</label>
            <textarea
              id="answer"
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              placeholder="Answer in your own words. Say “I'm not sure” if you aren't — Umbra will keep it open rather than guess."
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey) && answer.trim()) send(false);
              }}
            />
            <div className="row">
              <button className="btn primary" onClick={() => send(false)} disabled={busy || !answer.trim()}>
                Answer <span className="tiny faint" style={{ color: "inherit", opacity: 0.7 }}>⌘↵</span>
              </button>
              <MicButton onText={(t) => setAnswer((a) => (a ? a + " " : "") + t)} />
              {q.sample_answer && (
                <button className="btn ghost" onClick={() => setAnswer(q.sample_answer!)}>
                  Use Mira&apos;s answer <span className="tag seed">Seeded</span>
                </button>
              )}
              <span style={{ flex: 1 }} />
              <button className="btn ghost" onClick={() => send(true)} disabled={busy}>
                Skip — leave it open
              </button>
            </div>
          </section>
        ) : (
          <div className="card stack-sm">
            <h3>That&apos;s everything Umbra needed to ask.</h3>
            <p className="muted small">Next, Umbra repeats back what it learned so you can confirm or correct it.</p>
          </div>
        )}

        {(d.can_finish || !q) && (
          <div className="card glow row-between">
            <span className="small">
              {q ? `${d.progress.remaining} lower-priority question(s) left — answer them or finish now.` : "Ready for the teach-back."}
            </span>
            <button className="btn primary" onClick={finish} disabled={busy}>
              Finish debrief → teach-back
            </button>
          </div>
        )}

        <AgentPanel role="interviewer" context={agentContext} onUserMessage={(t) => setAnswer((a) => (a ? a + " " : "") + t)} />
      </div>

      <aside className="stack">
        {d.covered.length > 0 && (
          <div className="card stack-sm">
            <h4>Not asked — you already said it</h4>
            {d.covered.map((c, i) => (
              <div key={i} className="stack-sm small">
                <span className="muted" style={{ textDecoration: "line-through" }}>{c.text}</span>
                <span>{c.reason}</span>
              </div>
            ))}
          </div>
        )}
        {(d.answered.length > 0 || d.answered_live.length > 0) && (
          <div className="card stack-sm">
            <h4>Answered</h4>
            {[...d.answered_live, ...d.answered].map((a) => (
              <div key={a.id} className="stack-sm small">
                <span className="muted">{a.text}</span>
                <span className="quote">{a.answer}</span>
              </div>
            ))}
          </div>
        )}
        {d.skipped.length > 0 && (
          <div className="card stack-sm">
            <h4>Left open</h4>
            {d.skipped.map((a) => (
              <p key={a.id} className="small muted">{a.text}</p>
            ))}
          </div>
        )}
        <p className="tiny faint">Questions are ranked by risk: never-dos and escalation first, then thresholds and exceptions, then reasons. Duplicates and anything you already explained are dropped.</p>
      </aside>
      <Toast message={toast} onDone={() => setToast(null)} />
    </div>
  );
}

/* ================================================================================================ teach-back */

const KIND_LABEL: Record<TeachItem["kind"], string> = {
  workflow: "The workflow",
  observed_decision: "What I saw you do",
  expert_answer: "What you told me",
  open_question: "Still open",
};

function TeachbackView({ tb, setTb, id }: { tb: Teachback; setTb: (t: Teachback) => void; id: string }) {
  const router = useRouter();
  const [toast, setToast] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const committed = tb.session.status === "committed";
  const reviewed = tb.items.filter((i) => i.status !== "pending" || !i.confirmable).length;

  async function update(item: TeachItem, status: string, text?: string) {
    try {
      const r = await api<TeachItem>(`/teachback/${item.id}`, { method: "PATCH", json: { status, text } });
      setTb({ ...tb, items: tb.items.map((i) => (i.id === r.id ? r : i)) });
    } catch (e) {
      setToast(e instanceof ApiError ? e.message : "Couldn't update");
    }
  }

  async function commit() {
    setBusy(true);
    try {
      const r = await post<{ lit: string[] }>(`/sessions/${id}/commit`);
      sessionStorage.setItem("umbra:lit", JSON.stringify(r.lit));
      router.push("/map");
    } catch (e) {
      setToast(e instanceof ApiError ? e.message : "Couldn't commit");
      setBusy(false);
    }
  }

  return (
    <div className="split">
      <div className="stack">
        <div className="card tight small muted">
          Here&apos;s what I understood, in my own words. Confirm what&apos;s right, edit what&apos;s off, reject what&apos;s wrong.{" "}
          <strong style={{ color: "var(--text)" }}>Only confirmed items light up the Work Map</strong>; anything you were unsure
          about stays visibly open. <span className={`tag ${tb.generator.startsWith("model") ? "model" : "seed"}`}>{tb.generator}</span>
        </div>
        {tb.items.map((item) => (
          <TeachItemCard key={item.id} item={item} disabled={committed} onUpdate={update} />
        ))}
      </div>
      <aside className="stack sticky">
        <div className="card glow stack">
          <h3>{committed ? "Committed to the Work Map" : "Ready to commit?"}</h3>
          <p className="small muted">
            {reviewed} of {tb.items.length} items reviewed. Pending items are saved as <em>needs confirmation</em>; rejected ones
            are recorded as open questions.
          </p>
          {committed ? (
            <Link className="btn primary" href="/map">Open the Work Map →</Link>
          ) : (
            <button className="btn primary" onClick={commit} disabled={busy}>
              {busy ? "Lighting the map…" : "Commit to Work Map"}
            </button>
          )}
        </div>
        <div className="card tight stack-sm small">
          <span className="row" style={{ gap: 6 }}><span className="tag expert">Expert said</span> your exact words, quoted</span>
          <span className="row" style={{ gap: 6 }}><span className="tag observed">Observed</span> what was on screen</span>
          <span className="row" style={{ gap: 6 }}><span className="tag inference">AI inference</span> Umbra&apos;s restatement — never a quote</span>
        </div>
      </aside>
      <Toast message={toast} onDone={() => setToast(null)} />
    </div>
  );
}

function TeachItemCard({ item, disabled, onUpdate }: { item: TeachItem; disabled: boolean; onUpdate: (i: TeachItem, s: string, t?: string) => void }) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(item.text);
  const done = item.status === "confirmed" || item.status === "edited";
  return (
    <article className={`card stack-sm ${done ? "glow" : ""} ${item.kind === "open_question" ? "amber" : ""}`} aria-label={KIND_LABEL[item.kind]}>
      <div className="row-between">
        <div className="row" style={{ gap: 6 }}>
          <span className="eyebrow">{KIND_LABEL[item.kind]}</span>
          <ProvenanceTag p={item.provenance} confirmed={done} by={item.generator} />
          {item.confidence !== "high" && item.kind !== "open_question" && (
            <span className={`tag ${item.confidence === "low" ? "danger" : "inference"}`}>{item.confidence} confidence</span>
          )}
        </div>
        <span className={`tag ${done ? "accent" : item.status === "rejected" ? "danger" : ""}`}>{item.status}</span>
      </div>

      {editing ? (
        <div className="stack-sm">
          <textarea value={text} onChange={(e) => setText(e.target.value)} aria-label="Edit teach-back" />
          <span className="tiny faint">Your edit is stored as your own statement.</span>
        </div>
      ) : (
        <p className={item.provenance === "expert_statement" ? "quote" : "inference"} style={{ fontSize: 15.5 }}>
          {item.text}
        </p>
      )}

      {item.unresolved.length > 0 && (
        <div className="unresolved">
          <strong>{item.kind === "open_question" ? "Unanswered — " : "Not confirmed — you sounded unsure: "}</strong>
          {item.unresolved.join(" ")}
          <div className="tiny" style={{ marginTop: 4 }}>This stays as an open question on the skill card.</div>
        </div>
      )}

      {item.sources.length > 0 && (
        <details className="small">
          <summary className="faint" style={{ cursor: "pointer" }}>Evidence ({item.sources.length})</summary>
          <ul className="stack-sm" style={{ listStyle: "none", padding: 0, marginTop: 8 }}>
            {item.sources.map((s, i) => (
              <li key={i} className="row" style={{ alignItems: "baseline", flexWrap: "nowrap" }}>
                {s.clock && <span className="mono faint">{s.clock}</span>}
                <span className={s.kind === "expert_statement" ? "quote" : "muted"}>{s.text}</span>
                <span className={`tag ${s.kind === "expert_statement" ? "expert" : "observed"}`}>{s.kind === "expert_statement" ? "Expert said" : "Observed"}</span>
              </li>
            ))}
          </ul>
        </details>
      )}

      {!disabled && item.kind !== "open_question" && (
        <div className="row">
          {editing ? (
            <>
              <button className="btn sm primary" onClick={() => { onUpdate(item, "edited", text); setEditing(false); }} disabled={!text.trim()}>Save correction</button>
              <button className="btn sm ghost" onClick={() => { setEditing(false); setText(item.text); }}>Cancel</button>
            </>
          ) : (
            <>
              <button className="btn sm primary" onClick={() => onUpdate(item, "confirmed")} disabled={!item.confirmable || done} title={item.confirmable ? "" : "Uncertain knowledge can't be confirmed"}>
                ✓ Confirm
              </button>
              <button className="btn sm" onClick={() => setEditing(true)}>Correct it</button>
              <button className="btn sm danger" onClick={() => onUpdate(item, "rejected")} disabled={item.status === "rejected"}>Reject</button>
              {item.status !== "pending" && (
                <button className="btn sm ghost" onClick={() => onUpdate(item, "pending")}>Undo</button>
              )}
            </>
          )}
        </div>
      )}
    </article>
  );
}
