"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { api, ApiError, post } from "@/lib/api";
import { ErrorState, Loading } from "@/components/ui";

interface Brief {
  role: string;
  instructions: string;
  consent: string[];
  retention_days: number;
  rubric: { skill: string; title: string; criterion: string; ready: boolean }[];
  ready: boolean;
  task_count: number;
}

export default function TrialStart() {
  const router = useRouter();
  const [b, setB] = useState<Brief | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [alias, setAlias] = useState("");
  const [consent, setConsent] = useState(false);
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const load = useCallback(() => {
    api<Brief>("/trial/brief").then((x) => { setB(x); setError(null); }).catch(setError);
  }, []);
  useEffect(load, [load]);

  async function start() {
    setBusy(true);
    setMsg(null);
    try {
      const r = await post<{ token: string }>("/trial/candidates", { alias, consent });
      router.push(`/trial/${r.token}`);
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : "Couldn't start");
      setBusy(false);
    }
  }

  async function prepare() {
    setBusy(true);
    try {
      await post("/demo/fast-forward");
      load();
    } finally {
      setBusy(false);
    }
  }

  if (error) return <main id="main" className="container"><ErrorState error={error} onRetry={load} /></main>;
  if (!b) return <main id="main" className="container"><Loading /></main>;

  return (
    <main id="main" className="container stack-lg">
      <div className="row-between">
        <div className="stack-sm">
          <span className="eyebrow amber">Trial · skills assessment</span>
          <h1>{b.role}</h1>
          <p className="muted" style={{ maxWidth: 680 }}>{b.instructions} {b.task_count} cases, about 10 minutes.</p>
        </div>
        <Link href="/trial/review" className="btn">Reviewer console →</Link>
      </div>

      {!b.ready && (
        <div className="card amber stack-sm" role="status">
          <h3>The rubric isn&apos;t ready yet</h3>
          <p className="small muted">
            Trial uses the expert-confirmed Work Map as its rubric. Some assessed skills still need expert confirmation:{" "}
            {b.rubric.filter((r) => !r.ready).map((r) => r.title).join(", ")}.
          </p>
          <div className="row">
            <Link href="/capture" className="btn">Capture a session</Link>
            <button className="btn primary" onClick={prepare} disabled={busy}>{busy ? "Preparing…" : "Load Mira's confirmed sample map"}</button>
          </div>
        </div>
      )}

      <div className="split">
        <div className="stack">
          <section className="card stack" aria-labelledby="rubric-h">
            <h3 id="rubric-h">What we look for — the rubric</h3>
            <p className="small muted">Every candidate is assessed against the same skills, from the same expert-confirmed map.</p>
            {b.rubric.map((r) => (
              <div key={r.skill} className="stack-sm" style={{ borderLeft: "2px solid var(--line-2)", paddingLeft: 12 }}>
                <strong>{r.title}</strong>
                <span className="small muted">{r.criterion}</span>
              </div>
            ))}
            <p className="tiny faint">Reviewers record, per skill, whether your action and written reasoning demonstrate it. There is no overall score.</p>
          </section>
        </div>
        <aside className="stack">
          <section className="card amber stack">
            <h3>Before you begin</h3>
            <ul className="small muted stack-sm" style={{ paddingLeft: 18, margin: 0 }}>
              {b.consent.map((c) => <li key={c}>{c}</li>)}
            </ul>
            <label className="field">
              Name or alias (anything you like)
              <input type="text" value={alias} onChange={(e) => setAlias(e.target.value)} maxLength={60} placeholder="e.g. Candidate 7" />
            </label>
            <label className="row small" style={{ cursor: "pointer", alignItems: "flex-start", flexWrap: "nowrap" }}>
              <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} style={{ marginTop: 4 }} />
              <span>I understand what is recorded and consent to a human reviewing my responses for this role.</span>
            </label>
            {msg && <p className="small" style={{ color: "var(--danger)" }} role="alert">{msg}</p>}
            <button className="btn primary" onClick={start} disabled={!consent || busy || !b.ready}>Begin assessment</button>
          </section>
          <section className="card tight stack-sm">
            <label className="field">
              Already took it? Enter your receipt code to view or delete your data
              <div className="row" style={{ flexWrap: "nowrap" }}>
                <input type="text" value={code} onChange={(e) => setCode(e.target.value.trim())} />
                <button className="btn" disabled={!code} onClick={() => router.push(`/trial/${code}`)}>Open</button>
              </div>
            </label>
          </section>
        </aside>
      </div>
    </main>
  );
}
