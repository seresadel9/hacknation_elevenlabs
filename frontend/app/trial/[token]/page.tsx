"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError, nowMs, post, secondsSince } from "@/lib/api";
import type { InvoiceDocument, Option } from "@/lib/types";
import { InvoiceDoc } from "@/components/InvoiceDoc";
import { ConfirmDialog, ErrorState, Loading } from "@/components/ui";

interface Task {
  id: string;
  title: string;
  document: InvoiceDocument;
  actions: Option[];
  skill: string;
  submitted: boolean;
}

interface View {
  alias: string;
  status: "in_progress" | "submitted";
  retain_until: string;
  tasks: Task[];
  rubric: { skill: string; title: string; criterion: string }[];
  my_responses: { task_id: string; action_id: string; rationale: string; created_at: string }[];
}

export default function TrialRun() {
  const { token } = useParams<{ token: string }>();
  const router = useRouter();
  const [v, setV] = useState<View | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [action, setAction] = useState<string | null>(null);
  const [rationale, setRationale] = useState("");
  const [path, setPath] = useState<{ action_id: string; t: number }[]>([]);
  const [busy, setBusy] = useState(false);
  const [recorded, setRecorded] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const started = useRef(0);

  const load = useCallback(() => {
    api<View>(`/trial/candidates/${token}`)
      .then((x) => {
        setV(x);
        setError(null);
        if (!started.current) started.current = nowMs();
      })
      .catch(setError);
  }, [token]);
  useEffect(load, [load]);

  const task = v?.tasks.find((t) => !t.submitted);
  const done = v ? v.tasks.filter((t) => t.submitted).length : 0;

  async function submit() {
    if (!task || !action) return;
    setBusy(true);
    setMsg(null);
    try {
      await post(`/trial/candidates/${token}/responses`, {
        task_id: task.id, action_id: action, rationale, path, time_spent_s: secondsSince(started.current),
      });
      // Neutral acknowledgement only — the same message whatever was chosen.
      setRecorded(true);
      setAction(null);
      setRationale("");
      setPath([]);
      started.current = nowMs();
      load();
      window.setTimeout(() => setRecorded(false), 1800);
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : "Couldn't record the response");
    } finally {
      setBusy(false);
    }
  }

  async function finish() {
    await post(`/trial/candidates/${token}/finish`);
    load();
  }

  async function del() {
    setConfirmDelete(false);
    await api(`/trial/candidates/${token}`, { method: "DELETE" });
    router.push("/trial");
  }

  if (error) return <main id="main" className="container"><ErrorState error={error} onRetry={load} /></main>;
  if (!v) return <main id="main" className="container"><Loading /></main>;

  return (
    <main id="main" className="container stack-lg">
      <div className="row-between">
        <div className="stack-sm">
          <span className="eyebrow amber">Trial · {v.alias}</span>
          <h1 style={{ fontSize: 30 }}>{v.status === "submitted" ? "Submitted — thank you" : task ? `Case ${done + 1} of ${v.tasks.length}: ${task.title}` : "All cases answered"}</h1>
        </div>
        <span className="pill mono">{done}/{v.tasks.length}</span>
      </div>

      {recorded && <div className="card tight amber small" role="status">Response recorded.</div>}

      {v.status === "in_progress" && task ? (
        <div className="split">
          <div className="stack">
            <InvoiceDoc doc={task.document} />
          </div>
          <section className="card amber stack" aria-labelledby="task-h">
            <h3 id="task-h">What do you do?</h3>
            <div className="stack-sm" role="radiogroup" aria-label="Your action">
              {task.actions.map((a) => (
                <button key={a.id} role="radio" aria-checked={action === a.id} className="choice"
                  onClick={() => { setAction(a.id); setPath((p) => [...p, { action_id: a.id, t: secondsSince(started.current) }]); }}>
                  <span className="radio" aria-hidden="true" />
                  <span>{a.label}</span>
                </button>
              ))}
            </div>
            <label className="field">
              Your reasoning — what in the documents decided it?
              <textarea value={rationale} onChange={(e) => setRationale(e.target.value)} maxLength={2000} />
            </label>
            {msg && <p className="small" style={{ color: "var(--danger)" }} role="alert">{msg}</p>}
            <button className="btn primary" disabled={!action || rationale.trim().length < 10 || busy} onClick={submit}>Submit this case</button>
            <p className="tiny faint">You won&apos;t see whether this was right — by design, so every candidate has the same conditions. Submitted cases can&apos;t be changed.</p>
          </section>
        </div>
      ) : v.status === "in_progress" ? (
        <div className="card amber stack">
          <p>You&apos;ve answered every case. Submit the assessment for human review.</p>
          <button className="btn primary" onClick={finish} style={{ alignSelf: "flex-start" }}>Submit assessment</button>
        </div>
      ) : (
        <div className="card amber stack">
          <p>Your responses are with a human reviewer. Umbra doesn&apos;t score you or make a hiring decision.</p>
          <p className="small muted">
            Receipt code: <code className="kbd">{token}</code> — keep it to view or delete your data. Data is deleted automatically after{" "}
            {new Date(v.retain_until).toLocaleDateString()}.
          </p>
        </div>
      )}

      <section className="card tight stack-sm">
        <div className="row-between">
          <h4>Your data</h4>
          <button className="btn sm danger" onClick={() => setConfirmDelete(true)}>Delete my data</button>
        </div>
        {v.my_responses.length === 0 ? (
          <p className="small faint">Nothing recorded yet.</p>
        ) : (
          v.my_responses.map((r) => (
            <p key={r.task_id} className="small muted">
              <span className="mono">{r.task_id}</span> · {v.tasks.find((t) => t.id === r.task_id)?.actions.find((a) => a.id === r.action_id)?.label} — “{r.rationale}”
            </p>
          ))
        )}
        <p className="tiny faint">Recorded: chosen action, the order of your choices, rationale, time per case. Kept until {new Date(v.retain_until).toLocaleDateString()}.</p>
      </section>
      <p className="small"><Link href="/trial">← Trial home</Link></p>
      <ConfirmDialog open={confirmDelete} title="Delete your assessment data?" body="Your responses are permanently deleted and removed from the reviewer console." confirmLabel="Delete" danger onConfirm={del} onCancel={() => setConfirmDelete(false)} />
    </main>
  );
}
