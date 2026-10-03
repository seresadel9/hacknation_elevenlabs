"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { InvoiceDocument, Option } from "@/lib/types";
import { ConfirmDialog, Toast } from "@/components/ui";

interface Row {
  id: string;
  alias: string;
  status: string;
  started_at: string;
  submitted_at: string | null;
  retain_until: string;
  responses: number;
  of: number;
}

interface Detail {
  candidate: { id: string; alias: string; status: string; consent_at: string; retain_until: string };
  tasks: {
    task: { id: string; title: string; document: InvoiceDocument; actions: Option[]; skill: string };
    skill_title: string;
    expected_action: string;
    expert_rules: { node: string; text: string }[];
    response: { action: string; rationale: string; path: { action_id: string; t: number }[]; time_spent_s: number | null; submitted_at: string } | null;
    evidence_level: "demonstrated" | "partially_demonstrated" | "not_demonstrated" | "not_assessed";
    matched_cues: string[];
  }[];
  rubric: { skill: string; title: string; criterion: string }[];
  notice: string;
}

const LEVEL_TEXT = {
  demonstrated: "Demonstrated",
  partially_demonstrated: "Partially demonstrated",
  not_demonstrated: "Not demonstrated",
  not_assessed: "Not assessed",
};

export default function ReviewConsole() {
  const [code, setCode] = useState("");
  const [authed, setAuthed] = useState<string | null>(null);
  const [rows, setRows] = useState<Row[] | null>(null);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [confirmDel, setConfirmDel] = useState(false);

  const headers = useCallback((c: string) => ({ "x-reviewer-code": c }), []);

  const load = useCallback(async (c: string) => {
    try {
      const r = await api<Row[]>("/trial/review", { headers: headers(c) });
      setRows(r);
      setAuthed(c);
      setErr(null);
      sessionStorage.setItem("umbra:reviewer", c);
    } catch (e) {
      setErr(e instanceof ApiError && e.status === 403 ? "That access code isn't valid." : e instanceof ApiError ? e.message : "Couldn't load");
      setAuthed(null);
    }
  }, [headers]);

  useEffect(() => {
    const saved = sessionStorage.getItem("umbra:reviewer");
    if (saved) load(saved);
  }, [load]);

  async function open(id: string) {
    if (!authed) return;
    try {
      setDetail(await api<Detail>(`/trial/review/${id}`, { headers: headers(authed) }));
    } catch (e) {
      setToast(e instanceof ApiError ? e.message : "Couldn't open");
    }
  }

  async function remove() {
    if (!authed || !detail) return;
    setConfirmDel(false);
    await api(`/trial/review/${detail.candidate.id}`, { method: "DELETE", headers: headers(authed) });
    setDetail(null);
    setToast("Candidate data deleted.");
    load(authed);
  }

  if (!authed)
    return (
      <main id="main" className="container stack-lg" style={{ maxWidth: 520 }}>
        <div className="stack-sm">
          <span className="eyebrow amber">Trial · reviewer console</span>
          <h1 style={{ fontSize: 30 }}>Authorized reviewers only</h1>
          <p className="muted small">Candidate evidence is visible only with a reviewer access code.</p>
        </div>
        <form className="card amber stack" onSubmit={(e) => { e.preventDefault(); load(code); }}>
          <label className="field">
            Access code
            <input type="password" value={code} onChange={(e) => setCode(e.target.value)} autoComplete="off" />
          </label>
          {err && <p className="small" role="alert" style={{ color: "var(--danger)" }}>{err}</p>}
          <button className="btn primary" disabled={!code}>Open console</button>
          <p className="tiny faint">Demo code: <code>umbra-review-demo</code> (set <code>REVIEWER_ACCESS_CODE</code> in <code>backend/.env</code> to change it).</p>
        </form>
      </main>
    );

  return (
    <main id="main" className="container stack-lg">
      <div className="row-between">
        <div className="stack-sm">
          <span className="eyebrow amber">Trial · reviewer console</span>
          <h1 style={{ fontSize: 30 }}>Candidate evidence</h1>
        </div>
        <button className="btn ghost sm" onClick={() => { sessionStorage.removeItem("umbra:reviewer"); setAuthed(null); setDetail(null); }}>Sign out</button>
      </div>
      <div className="card tight amber small">
        Evidence for human review only. Umbra computes no overall score, infers no personality or protected traits, and makes
        no hire/reject recommendation. You decide.
      </div>

      <div className="split">
        <div className="stack">
          {detail ? (
            <>
              <div className="row-between">
                <div className="stack-sm">
                  <h2>{detail.candidate.alias}</h2>
                  <span className="small muted">
                    Consented {new Date(detail.candidate.consent_at).toLocaleString()} · retained until{" "}
                    {new Date(detail.candidate.retain_until).toLocaleDateString()} · {detail.candidate.status}
                  </span>
                </div>
                <button className="btn sm danger" onClick={() => setConfirmDel(true)}>Delete candidate data</button>
              </div>
              {detail.tasks.map((t) => (
                <article key={t.task.id} className="card stack-sm">
                  <div className="row-between">
                    <div className="stack-sm" style={{ gap: 2 }}>
                      <span className="eyebrow amber">{t.task.id} · {t.skill_title}</span>
                      <h3>{t.task.title} <span className="muted small">({t.task.document.number} · {t.task.document.supplier})</span></h3>
                    </div>
                    <span className={`evidence-chip ${t.evidence_level}`}>{LEVEL_TEXT[t.evidence_level]}</span>
                  </div>
                  {t.response ? (
                    <div className="grid-2">
                      <div className="stack-sm">
                        <h4>Candidate</h4>
                        <p><span className="faint small">Action:</span> {t.response.action}</p>
                        <p className="quote">{t.response.rationale}</p>
                        <h4 style={{ marginTop: 6 }}>Path</h4>
                        <ol className="timeline">
                          {t.response.path.map((p, i) => (
                            <li key={i}><span className="mono faint">+{p.t}s</span> selected “{t.task.actions.find((a) => a.id === p.action_id)?.label}”</li>
                          ))}
                          <li><span className="mono faint">+{t.response.time_spent_s ?? "?"}s</span> submitted</li>
                        </ol>
                      </div>
                      <div className="stack-sm">
                        <h4>Rubric reference (reviewer-only)</h4>
                        <p className="small"><span className="faint">Expert action:</span> {t.expected_action}</p>
                        {t.expert_rules.map((r, i) => (
                          <p key={i} className="small quote">{r.text}</p>
                        ))}
                        <p className="tiny faint">
                          Assistive signal — factors named in the rationale: {t.matched_cues.length ? t.matched_cues.join(", ") : "none detected"}. Read the rationale; don&apos;t rely on this.
                        </p>
                      </div>
                    </div>
                  ) : (
                    <p className="small faint">Not answered.</p>
                  )}
                </article>
              ))}
            </>
          ) : (
            <div className="card state"><div className="icon">◇</div><p className="muted small">Select a candidate to review their path and per-skill evidence.</p></div>
          )}
        </div>
        <aside className="stack">
          <div className="card stack-sm">
            <h4>Candidates</h4>
            {rows && rows.length === 0 && <p className="small faint">No candidates yet. <Link href="/trial">Take the Trial</Link> to create one.</p>}
            {rows?.map((r) => (
              <button key={r.id} className="choice" aria-pressed={detail?.candidate.id === r.id} onClick={() => open(r.id)}>
                <span className="stack-sm" style={{ gap: 2 }}>
                  <strong>{r.alias}</strong>
                  <span className="tiny faint">{r.responses}/{r.of} cases · {r.status} · deletes {new Date(r.retain_until).toLocaleDateString()}</span>
                </span>
              </button>
            ))}
          </div>
          {detail && (
            <div className="card stack-sm">
              <h4>Rubric (shown to candidates)</h4>
              {detail.rubric.map((r) => (
                <p key={r.skill} className="small"><strong>{r.title}</strong> — <span className="muted">{r.criterion}</span></p>
              ))}
            </div>
          )}
        </aside>
      </div>
      <ConfirmDialog open={confirmDel} title="Delete this candidate's data?" body="All responses and the consent record are permanently deleted." confirmLabel="Delete" danger onConfirm={remove} onCancel={() => setConfirmDel(false)} />
      <Toast message={toast} onDone={() => setToast(null)} />
    </main>
  );
}
