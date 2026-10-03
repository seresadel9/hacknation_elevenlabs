"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError, nowMs, post, secondsSince } from "@/lib/api";
import type { Citation, GraphNode, LevelState, Scenario } from "@/lib/types";
import { InvoiceDoc } from "@/components/InvoiceDoc";
import { ErrorState, Loading, Toast } from "@/components/ui";
import { AgentPanel, SpeakButton } from "@/components/VoiceTools";

interface LevelDetail {
  level: LevelState;
  scenarios: Scenario[];
  rubric: { id: string; label: string }[];
  skill_card?: GraphNode;
}

interface Precheck {
  intervene: boolean;
  message?: string;
  guardrail?: { key: string; title: string };
  citations?: Citation[];
  generator?: string;
}

interface Result {
  attempt_id: string;
  action_correct: boolean;
  reason_correct: boolean;
  guardrails_missed: { key: string; title: string }[];
  tutor_intervened: boolean;
  correct_action: string;
  correct_reason: string;
  explanation: string;
  citations: Citation[];
  mode: "learn" | "practice";
  level: LevelState;
}

interface Summary {
  level: LevelState;
  rubric: { id: string; label: string; met: boolean }[];
  scenarios: { id: string; title: string; attempted: boolean; action_correct: boolean; reason_correct: boolean; tutor_intervened: boolean; chosen: string | null; attempt_id: string | null; at: string | null }[];
  demonstrated_skills: string[];
  missed_guardrails: { key: string; title: string }[];
  practice_next: string[];
  why: string;
  practice_attempts: number;
}

type PathStep = { action_id: string; reason_id?: string | null; prechecked?: boolean; t: number };

export default function LevelPage() {
  const { level } = useParams<{ level: string }>();
  const [d, setD] = useState<LevelDetail | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [idx, setIdx] = useState(0);
  const [action, setAction] = useState<string | null>(null);
  const [reason, setReason] = useState<string | null>(null);
  const [path, setPath] = useState<PathStep[]>([]);
  const [check, setCheck] = useState<Precheck | null>(null);
  const [result, setResult] = useState<Result | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [mode, setMode] = useState<"learn" | "practice">("learn");
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const started = useRef(0);

  const load = useCallback(() => {
    api<LevelDetail>(`/illuminate/levels/${level}`)
      .then((r) => {
        setD(r);
        started.current = nowMs();
        setMode(r.level.status === "mastered" ? "practice" : "learn");
        setError(null);
      })
      .catch(setError);
  }, [level]);
  useEffect(load, [load]);

  const sc = d?.scenarios[idx];

  function resetScenario(i: number) {
    setIdx(i);
    setAction(null);
    setReason(null);
    setPath([]);
    setCheck(null);
    setResult(null);
    started.current = nowMs();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function choose(a: string) {
    setAction(a);
    setCheck(null);
    setPath((p) => [...p, { action_id: a, t: secondsSince(started.current) }]);
  }

  async function checkAndSubmit(force = false) {
    if (!sc || !action) return;
    setBusy(true);
    try {
      if (!force) {
        const pc = await post<Precheck>("/illuminate/precheck", { scenario_id: sc.id, action_id: action });
        const step = { action_id: action, reason_id: reason, prechecked: true, t: secondsSince(started.current) };
        const nextPath = [...path, step];
        setPath(nextPath);
        if (pc.intervene) {
          setCheck(pc);
          setBusy(false);
          return;
        }
        await submit(nextPath);
      } else {
        await submit(path);
      }
    } catch (e) {
      setToast(e instanceof ApiError ? e.message : "Couldn't submit");
    } finally {
      setBusy(false);
    }
  }

  async function submit(p: PathStep[]) {
    if (!sc || !action) return;
    const r = await post<Result>("/illuminate/submit", { scenario_id: sc.id, action_id: action, reason_id: reason, path: p, mode });
    setResult(r);
    setCheck(null);
    setD((prev) => (prev ? { ...prev, level: r.level } : prev));
  }

  async function showSummary() {
    try {
      setSummary(await api<Summary>(`/illuminate/levels/${level}/summary`));
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (e) {
      setToast(e instanceof ApiError ? e.message : "Couldn't load summary");
    }
  }

  if (error) return <main id="main" className="container"><ErrorState error={error} onRetry={load} /></main>;
  if (!d) return <main id="main" className="container"><Loading label="Loading mission" /></main>;

  const locked = d.scenarios.length === 0;
  return (
    <main id="main" className="container stack-lg" data-mode="illuminate">
      <div className="row-between">
        <div className="stack-sm">
          <Link href="/illuminate" className="small">← Skill map</Link>
          <span className="eyebrow violet">Mission {d.level.order} · {d.level.subtitle}</span>
          <h1 style={{ fontSize: 32 }}>{d.level.title}</h1>
          <p className="muted">{d.level.goal}</p>
        </div>
        {!locked && !summary && (
          <div className="stack-sm" style={{ alignItems: "flex-end" }}>
            <div className="tabs" role="tablist" aria-label="Attempt mode">
              <button role="tab" aria-selected={mode === "learn"} onClick={() => setMode("learn")}>Learn</button>
              <button role="tab" aria-selected={mode === "practice"} onClick={() => setMode("practice")}>Practice replay</button>
            </div>
            <span className="tiny faint">{mode === "practice" ? "Practice is recorded but never changes your progress." : "Attempts count toward mastery."}</span>
          </div>
        )}
      </div>

      {locked ? (
        <div className="card stack">
          <h3>{d.level.status === "awaiting_expert" ? "Waiting on the expert" : "Locked — here's what you need first"}</h3>
          {d.level.lock_reasons.map((r) => <p key={r} className="muted">{r}</p>)}
          <p className="small faint">Locks show prerequisites only — never the answers.</p>
          <div className="row">
            {d.level.missing_confirmation.length > 0 && <Link className="btn" href="/map">Open the Work Map</Link>}
            {d.level.missing_prereqs.length > 0 && <Link className="btn violet" href="/illuminate">Back to the skill map</Link>}
          </div>
        </div>
      ) : summary ? (
        <SummaryView s={summary} onReplay={() => { setSummary(null); resetScenario(0); }} />
      ) : sc ? (
        <div className="split-wide">
          <div className="stack">
            <div className="row" style={{ gap: 6 }} aria-label="Cases in this mission">
              {d.scenarios.map((s, i) => (
                <span key={s.id} className={`tag ${i === idx ? "violet" : ""}`}>Case {i + 1}: {s.title}</span>
              ))}
              <span className="tag seed">Seeded scenario</span>
            </div>
            <InvoiceDoc doc={sc.document} glOverride={action?.startsWith("recode-0720") ? "0720" : undefined} />

            <section className="card stack" aria-labelledby="predict-h">
              <div className="row-between">
                <h3 id="predict-h">Predict first: {sc.prompt}</h3>
              </div>
              <div className="stack-sm" role="radiogroup" aria-label="Your action">
                {sc.actions.map((a) => (
                  <button key={a.id} role="radio" aria-checked={action === a.id} className="choice" onClick={() => choose(a.id)} disabled={!!result}>
                    <span className="radio" aria-hidden="true" />
                    <span>{a.label}</span>
                  </button>
                ))}
              </div>
              <h4 style={{ marginTop: 6 }}>Why?</h4>
              <div className="stack-sm" role="radiogroup" aria-label="Your reason">
                {sc.reasons.map((r) => (
                  <button key={r.id} role="radio" aria-checked={reason === r.id} className="choice" onClick={() => setReason(r.id)} disabled={!!result}>
                    <span className="radio" aria-hidden="true" />
                    <span>{r.label}</span>
                  </button>
                ))}
              </div>

              {check?.intervene && (
                <div className="intervention stack-sm" role="alert">
                  <div className="row-between">
                    <span className="eyebrow violet">Tutor · before you submit</span>
                    <SpeakButton text={check.message ?? ""} autoPlay />
                  </div>
                  <p style={{ fontSize: 16 }}>{check.message}</p>
                  {check.citations?.map((c, i) => <CitationLine key={i} c={c} />)}
                  <div className="row">
                    <button className="btn violet" onClick={() => setCheck(null)}>Let me reconsider</button>
                    <Link className="btn sm ghost" href={`/map#${check.guardrail?.key}`} target="_blank">Open skill card ↗</Link>
                    <span style={{ flex: 1 }} />
                    <button className="btn sm ghost" onClick={() => checkAndSubmit(true)} disabled={busy}>Submit anyway</button>
                  </div>
                </div>
              )}

              {!result && !check && (
                <div className="row">
                  <button className="btn violet" onClick={() => checkAndSubmit(false)} disabled={!action || !reason || busy}>
                    {busy ? "Checking…" : "Check & submit"}
                  </button>
                  <span className="tiny faint">The tutor reviews consequential choices before anything is submitted.</span>
                </div>
              )}
            </section>

            {result && (
              <section className={`card stack ${result.action_correct && result.reason_correct ? "glow" : "amber"}`} aria-live="polite">
                <div className="row" style={{ gap: 8 }}>
                  <span className={`tag ${result.action_correct ? "accent" : "danger"}`}>Action {result.action_correct ? "matches the expert" : "differs from the expert"}</span>
                  <span className={`tag ${result.reason_correct ? "accent" : "danger"}`}>Reason {result.reason_correct ? "matches" : "differs"}</span>
                  {result.tutor_intervened && <span className="tag violet">Tutor stepped in</span>}
                  {result.mode === "practice" && <span className="tag">Practice · not counted</span>}
                </div>
                {result.guardrails_missed.length > 0 && (
                  <div className="card tight danger small">Missed guardrail: {result.guardrails_missed.map((g) => g.title).join(", ")}</div>
                )}
                <div className="stack-sm">
                  <p><span className="faint small">Expert&apos;s action:</span> {result.correct_action}</p>
                  <p><span className="faint small">Expert&apos;s reason:</span> {result.correct_reason}</p>
                  <p className="muted">{result.explanation}</p>
                </div>
                {result.citations.map((c, i) => <CitationLine key={i} c={c} />)}
                <div className="row">
                  {idx < d.scenarios.length - 1 ? (
                    <button className="btn violet" onClick={() => resetScenario(idx + 1)}>Next case →</button>
                  ) : (
                    <button className="btn violet" onClick={showSummary}>Mission summary →</button>
                  )}
                  <button className="btn ghost" onClick={() => resetScenario(idx)}>Try this case again</button>
                </div>
              </section>
            )}
          </div>
          <TutorPanel scenario={sc} decided={!!result} skill={d.skill_card} />
        </div>
      ) : null}
      <Toast message={toast} onDone={() => setToast(null)} />
    </main>
  );
}

function CitationLine({ c }: { c: Citation }) {
  return (
    <div className="evidence-anchor" style={{ alignItems: "flex-start" }}>
      <span className="tag expert" style={{ flex: "none" }}>Expert-confirmed</span>
      <span className="stack-sm" style={{ gap: 2 }}>
        {c.quote ? <span className="quote">{c.quote}</span> : <span className="inference">{c.text}</span>}
        <span className="tiny faint">
          <Link href={`/map#${c.node}`}>{c.node_title}</Link>
          {c.clock ? ` · source moment ${c.clock}` : " · debrief statement"}
        </span>
      </span>
    </div>
  );
}

function TutorPanel({ scenario, decided, skill }: { scenario: Scenario; decided: boolean; skill?: GraphNode }) {
  const [msgs, setMsgs] = useState<{ who: "me" | "tutor"; text: string; citations?: Citation[] }[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setMsgs([{ who: "tutor", text: "I'm your tutor for this mission. I only use what Mira has confirmed — ask me anything, or tell me what you're thinking." }]);
  }, [scenario.id]);
  useEffect(() => endRef.current?.scrollIntoView({ block: "nearest" }), [msgs.length]);

  async function ask(text: string) {
    if (!text.trim()) return;
    setMsgs((m) => [...m, { who: "me", text }]);
    setInput("");
    setBusy(true);
    try {
      const r = await post<{ reply: string; citations: Citation[] }>("/illuminate/tutor", { message: text, scenario_id: scenario.id, decided });
      setMsgs((m) => [...m, { who: "tutor", text: r.reply, citations: r.citations }]);
    } catch {
      setMsgs((m) => [...m, { who: "tutor", text: "I can't reach the Work Map right now — try again in a moment." }]);
    } finally {
      setBusy(false);
    }
  }

  const last = msgs.filter((m) => m.who === "tutor").at(-1);
  const context = `You are Umbra's onboarding tutor. Scenario: ${scenario.prompt} Invoice ${scenario.document.number} from ${scenario.document.supplier}, net €${scenario.document.net}. ` +
    `Only use this expert-confirmed knowledge: ${JSON.stringify(skill?.card ?? {}).slice(0, 3000)}. Coach with questions before the learner decides.`;

  return (
    <aside className="card violet stack sticky" aria-label="AI teaching assistant">
      <div className="row-between">
        <span className="eyebrow violet">Teaching assistant</span>
        {last && <SpeakButton text={last.text} />}
      </div>
      <div className="chat" aria-live="polite">
        {msgs.map((m, i) => (
          <div key={i} className={`bubble ${m.who}`}>
            {m.text}
            {m.citations && m.citations.length > 0 && (
              <div className="tiny faint" style={{ marginTop: 6 }}>
                Grounded in: {m.citations.map((c) => c.node_title).join(", ")}
              </div>
            )}
          </div>
        ))}
        <div ref={endRef} />
      </div>
      <div className="row" style={{ gap: 6 }}>
        {["What should I look at first?", "Which rule applies here?", "Why does this matter?"].map((q) => (
          <button key={q} className="btn sm" onClick={() => ask(q)} disabled={busy}>{q}</button>
        ))}
      </div>
      <form className="row" style={{ flexWrap: "nowrap" }} onSubmit={(e) => { e.preventDefault(); ask(input); }}>
        <label className="sr-only" htmlFor="tutor-in">Ask the tutor</label>
        <input id="tutor-in" type="text" value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask about this invoice…" maxLength={1000} />
        <button className="btn violet" disabled={busy || !input.trim()}>Ask</button>
      </form>
      <AgentPanel role="tutor" context={context} />
      <p className="tiny faint">Grounded only in expert-confirmed cards. If Mira hasn&apos;t confirmed something, the tutor says so instead of guessing.</p>
    </aside>
  );
}

function SummaryView({ s, onReplay }: { s: Summary; onReplay: () => void }) {
  const mastered = s.level.status === "mastered";
  return (
    <div className="split">
      <section className={`card stack ${mastered ? "glow" : "violet"}`}>
        <span className="eyebrow">{mastered ? "Skill lit" : "Not lit yet"}</span>
        <h2>{mastered ? `${s.level.skill_title} — mastered` : s.level.skill_title}</h2>
        <p>{s.why}</p>
        <div className="stack-sm">
          <h4>Rubric</h4>
          {s.rubric.map((r) => (
            <div key={r.id} className={`rubric-line ${r.met ? "met" : ""}`}>
              <span className="mark" aria-hidden="true">{r.met ? "✓" : "·"}</span>
              <span>{r.label} <span className="sr-only">{r.met ? "met" : "not met"}</span></span>
            </div>
          ))}
        </div>
        <div className="stack-sm">
          <h4>Evidence behind this decision</h4>
          {s.scenarios.map((x) => (
            <div key={x.id} className="row small" style={{ alignItems: "baseline" }}>
              <span className={`tag ${x.action_correct && x.reason_correct ? "accent" : x.attempted ? "danger" : ""}`}>{x.attempted ? (x.action_correct && x.reason_correct ? "Matched" : "Differed") : "Not attempted"}</span>
              <strong>{x.title}</strong>
              {x.chosen && <span className="muted">— chose “{x.chosen}”</span>}
              {x.tutor_intervened && <span className="tag violet">tutor stepped in</span>}
              {x.attempt_id && <span className="tiny faint mono">{x.attempt_id}</span>}
            </div>
          ))}
          {s.practice_attempts > 0 && <p className="tiny faint">{s.practice_attempts} practice attempt(s) stored separately — they never change progress.</p>}
        </div>
      </section>
      <aside className="stack">
        {s.demonstrated_skills.length > 0 && (
          <div className="card stack-sm"><h4>Demonstrated</h4>{s.demonstrated_skills.map((x) => <p key={x}>✓ {x}</p>)}</div>
        )}
        <div className="card stack-sm">
          <h4>Missed guardrails</h4>
          {s.missed_guardrails.length ? s.missed_guardrails.map((g) => <Link key={g.key} href={`/map#${g.key}`}>{g.title}</Link>) : <p className="small muted">None — every guardrail held at submission.</p>}
        </div>
        <div className="card stack-sm">
          <h4>Practise next</h4>
          {s.practice_next.length ? s.practice_next.map((p) => <p key={p} className="small">{p}</p>) : <p className="small muted">Nothing outstanding here.</p>}
        </div>
        <div className="row">
          <Link className="btn violet" href="/illuminate">Back to the skill map</Link>
          <button className="btn" onClick={onReplay}>Replay</button>
        </div>
      </aside>
    </div>
  );
}
