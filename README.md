# Umbra

**Learn in the quiet. Master in the light.**

Umbra watches how experienced people make decisions while they work, holds every question until they're done,
confirms what it learned with them, and turns that into a living, glowing skill graph. New hires then light the
graph up through game-like onboarding (**Illuminate**), and candidates can be assessed against the same graph,
with no coaching at all (**Trial**).

Built for the ElevenLabs "AI Apprentice" challenge (Hack-Nation × ElevenLabs, 7th Global AI Hackathon).

> **The full demo runs with zero API keys.** Without credentials, Umbra uses deterministic, evidence-based
> fallbacks, and the UI labels them (`SIMULATED`, `SEEDED`, `AI INFERENCE`, "demo fallback"). All people,
> companies, invoices and IBANs are fictional.

---

## Quick start

Prerequisites: Python 3.11+ with [uv](https://docs.astral.sh/uv/), and Node 20+ (tested on Node 22).

```bash
# 1. Backend: FastAPI on :8000
cd backend
cp .env.example .env            # optional; every key may stay empty
uv sync
uv run uvicorn app.main:app --reload --port 8000

# 2. Frontend: Next.js on :3000 (second terminal)
cd frontend
npm install
npm run dev
```

Open <http://localhost:3000> and press **Try sample workflow**.

Or start both with one command: `bash scripts/dev.sh`. **Replit:** import the repo and press Run (`.replit` calls
`scripts/dev.sh`; it falls back to `pip` if `uv` is missing). The frontend sends `/api/*` to the backend through a
Next.js rewrite. Set `BACKEND_URL` if the backend isn't at `http://127.0.0.1:8000`, for example when the frontend is
on Vercel and the backend is hosted elsewhere.

## A five-minute walkthrough for judges

1. **Landing → Try sample workflow.** This creates a Lock-In session for "Mira, 24 years in AP", who processes five
   fictional invoices.
2. **Capture.** Read the "what will be observed" panel, then press **Start observing**. The UI stays dim; the only
   motion is one breathing indicator, and a counter shows the questions being held. No question text is shown.
   Press **Next moment** to skip through the simulated ten-minute session (the clock runs 8× faster, and this is
   labelled). Try **Off the record**, **Pause**, or **✕** on any logged moment to strike it.
3. **End session → Debrief.** A banner confirms that *Umbra asked you 0 questions during the session*. It then asks
   5 questions one at a time. Each question cites the moment it came from and is ranked by risk: never-dos and
   escalation come first. The side panel shows a question Umbra **didn't** ask, because Mira had already given the
   reason aloud at 02:21. Use **Use Mira's answer** to fill in the seeded answers.
4. **Teach-back.** The apprentice repeats back, in its own words, what it saw and what it was told. Confirm, correct,
   or reject each item. Mira's hedge ("software licences I'm not sure about") is **never confirmable**; it stays
   an open question on the card.
5. **Commit → Map.** Confirmed nodes move from dim drafts into the light. Click any node (or use **List / tree**) to
   open its skill card: thresholds, never-dos, escalation rules and exceptions, plus evidence timestamps. Each item
   is tagged *Expert said* (an exact quote), *Observed*, or *AI inference*.
6. **Illuminate.** Master *First light* (three-way match) to unlock *Capex or opex*. On the **€7,200 label printer
   pre-coded to opex**, choose "Approve as coded" and press **Check & submit**. The tutor steps in *before*
   submission and quotes Mira's confirmed €5,000-per-item rule, with a link to the skill card. The mission summary
   shows the mastery rubric and the stored attempts behind the unlock.
7. **Trial** (amber chrome, "Assessment mode — no coaching" banner). Give consent and work a case: you get only a
   neutral "Response recorded". Then open the **Reviewer console** (demo code `umbra-review-demo`). It shows the
   candidate's full path, rationale, per-skill evidence level and the rubric. There is no score and no hire/reject
   recommendation, and both candidate and reviewer can delete the data.

In a hurry? **Skip to the lit map** on the landing page runs the real capture → debrief → confirm pipeline with
Mira's seeded answers (`POST /api/demo/fast-forward`). **Reset demo data** clears everything.

---

## What's implemented

### Capture: Lock-In Mode and Live Coaching
- Setup screen: workflow name, mode choice, and a plain explanation of what is observed, what is stored and where it goes.
- Controls: start, pause/resume, end, discard, off the record (a time window), and strike any captured moment.
  Striking a moment also drops the questions that depended on it. There's an elapsed clock and a clear status pill.
- **The Lock-In invariant is enforced on the server.** While a Lock-In session runs, the API returns only
  `held_question_count`. Question text doesn't exist client-side until the debrief, and `/debrief` returns 409
  until the session ends. Tests check this.
- **Live Coaching** asks only at natural pauses (`activity == idle`), only about the invoice on screen, never while
  a question is still open, and no more than one per 120 work-seconds (≤ 5 per 10 min). The sample run asks 3:
  the €5,000 threshold, the Brightline variance and the Atlas never-do. A visible pacing log explains each
  "asked / held / silent" decision.
- Browser **screen sharing** (`getDisplayMedia`) with explicit permission and a persistent red "Sharing screen" pill.
  Frames are compared on the device (64×36 grayscale diff) to detect changes and natural pauses. Only when a vision
  model is configured is an occasional 640px JPEG sent, described in one sentence, and discarded. Permission-denied,
  unsupported and ended states are handled.
- Expert notes (and narration through Scribe v2 Realtime, when configured) are stored as *expert statements* and
  checked for coverage, so Umbra never asks for a reason the expert already gave.

### Evidence-based debrief and teach-back
- Gap types: **why, what would change it, threshold, exception, never-do, escalation, contradiction.**
- Each question is anchored to an observed moment and rendered with its real evidence (timestamp and the expert's
  own words). Priority = gap-type risk + amount (log scale) + hesitation signals − a penalty for generic questions.
  Duplicates are impossible (one per session and gap key), and covered questions are dropped and shown with the reason.
- The deterministic fallback is labelled "Evidence-based rules · demo fallback". With an LLM configured, custom
  workflows get extra model-generated questions, labelled as such.
- Teach-back items: the observed workflow, each observed decision (*AI inference*), and each answer split into
  card fields (thresholds / never / escalation / exceptions / why / how). Hedged sentences ("not sure", "maybe",
  "honestly…") are separated out and can never be confirmed. Edits are stored as expert statements.

### Work Map (knowledge graph)
- SQLite tables `nodes` (typed: skill, decision, guardrail, step, case, evidence) and `edges` (typed:
  prerequisite_for, depends_on, demonstrated_by, constrained_by, exception_to, supported_by_evidence).
- Status ladder **draft → needs confirmation → expert-confirmed** drives the visuals: dashed dim outlines, then
  violet, then cyan with bloom. On commit, the freshly confirmed nodes ignite one after another.
- Skill cards cover: meaning, when it applies, how, why, thresholds, exceptions, escalation, never, observations,
  evidence moments, open questions and relationships. Each item carries provenance; inferences are never shown in
  quotation marks.
- A clickable SVG graph with keyboard focus and a native tooltip on every node, type filters, and an accessible
  **list / tree** view (the default on phones).

### Illuminate (onboarding)
- 5 missions, 10 seeded scenarios. A mission unlocks only when (a) the guardrails it teaches are expert-confirmed
  and (b) its prerequisite skills are mastered. Locks explain what's needed and never reveal answers.
- Predict first (action + reason), then **Check & submit**: a consequential wrong choice triggers a tutor
  intervention *before* submission, quoting the confirmed card item and linking to it.
- The tutor chat is grounded only in confirmed knowledge, and its replies show which cards they draw on. If nothing
  confirmed applies, it says so instead of guessing.
- Mastery rubric (visible to the learner): expert's action on every case, expert's reason, no missed guardrail, at
  least one case solved without the tutor stepping in. Every attempt is stored with its full path; mastered
  progress is never downgraded; **Practice replay** attempts are stored separately and never change progress.

### Trial (recruiting assessment)
- Visually and structurally separate: amber accent, a striped "Assessment mode — no coaching" banner, and its own
  layout outside the Capture → Map → Illuminate stepper.
- Consent screen covering what's recorded, the 30-day retention and human-only review. The public rubric is shown
  at skill level; expected answers and cue words never leave the server for candidates (tested). Every submission
  gets the same neutral acknowledgement.
- Reviewer console (access-code gated): full path (each selection with a timestamp), rationale, time spent, and
  per-skill evidence (*Demonstrated / Partially / Not demonstrated / Not assessed*). It also shows the expert's
  confirmed rules as reviewer-only reference, plus an *assistive* cue match labelled "don't rely on this". There's
  no aggregate score, no inferred traits and no hire/reject output.
- Candidate self-service view/delete by receipt code, reviewer delete, and automatic purge after `retain_until`.

### Voice (ElevenLabs), when configured
| Feature | Used for | Endpoint |
|---|---|---|
| Text to Speech | Reading debrief questions and tutor interventions aloud | `POST /api/voice/tts` |
| Speech to Text (Scribe) | Answering debrief questions by voice | `POST /api/voice/stt` |
| Scribe v2 Realtime | Expert narration during capture; "speaking" suppresses Live Coaching questions | `POST /api/voice/scribe-token` (single-use token) |
| ElevenAgents | Voice interviewer (debrief) and voice tutor personas; Umbra context is sent as a contextual update | `GET /api/voice/agent-url?role=interviewer\|tutor` (signed URL) |

Without keys, these controls are hidden and the text experience is complete.

---

## Environment variables (`backend/.env`)

All are optional. Copy `backend/.env.example`. `.env` is gitignored; keys are read only by the backend and never
sent to the browser.

| Variable | Purpose |
|---|---|
| `ELEVENLABS_API_KEY` | Enables ElevenLabs. Scopes needed: ElevenAgents (Read/Write), Text to Speech (Access), Speech to Text (Access), Voices (Read/Write). |
| `ELEVENLABS_AGENT_ID_INTERVIEWER` | ElevenAgents agent for the voice debrief. |
| `ELEVENLABS_AGENT_ID_TUTOR` | ElevenAgents agent for the voice tutor. |
| `ELEVENLABS_VOICE_ID` | Voice for TTS. |
| `ELEVENLABS_TTS_MODEL`, `ELEVENLABS_STT_MODEL` | Optional overrides (defaults `eleven_flash_v2_5`, `scribe_v2`). |
| `LLM_PROVIDER` / `LLM_API_KEY` / `LLM_MODEL` | `anthropic` or `openai`. Used for teach-back paraphrase, tutor phrasing, intervention phrasing and custom-workflow questions. |
| `VISION_PROVIDER` / `VISION_API_KEY` / `VISION_MODEL` | `anthropic` or `openai`. Describes occasional shared-screen frames. |
| `DATABASE_URL` | Default `sqlite:///./umbra.db` (relative to `backend/`). |
| `REVIEWER_ACCESS_CODE` | Trial reviewer console code (default `umbra-review-demo`, a demo value). |
| `CANDIDATE_RETENTION_DAYS` | Default `30`. |

Frontend: `BACKEND_URL` (default `http://127.0.0.1:8000`) is read by `next.config.ts`.

For the ElevenAgents personas, create two agents in the ElevenLabs dashboard. Give them system prompts like *"You
are Umbra, a quiet, respectful apprentice. Ask exactly one question at a time from the context you are given."*
(interviewer) and *"Coach Socratically using only the expert-confirmed knowledge in your context; if it isn't
covered, say so."* (tutor). Umbra pushes the current question or confirmed card into the conversation as a
contextual update.

---

## Architecture

```
frontend/  Next.js 16 App Router · React 19 · TypeScript · plain CSS design tokens (no UI kit)
  app/                 /  /capture  /capture/[id]  /capture/[id]/debrief  /map  /illuminate  /illuminate/[level]
                       /trial  /trial/[token]  /trial/review
  components/          GraphView (layered SVG graph), SkillTree, SkillCard, InvoiceDoc, VoiceTools, VoiceNarration
  lib/                 api client, types, deterministic graph layout, screen-share + frame-diff hook
backend/   FastAPI · Pydantic · SQLite (stdlib sqlite3) · httpx
  app/main.py          routes
  app/capture.py       session lifecycle, Lock-In invariant, Live Coaching pacing, debrief
  app/questions.py     gap questions: generation, coverage detection, prioritisation, rendering
  app/language.py      transparent text heuristics (gap cues, hedges, apprentice voice)
  app/mapbuilder.py    draft nodes → teach-back → confirmed graph; graph queries
  app/illuminate.py    levels, unlock logic, interventions, grounded tutor, mastery rubric
  app/trial.py         assessment, consent/retention, reviewer evidence
  app/integrations.py  ElevenLabs / LLM / vision (all optional, all server-side)
  app/demo_script.py   SEEDED: Mira's simulated session, gap catalogue, node catalogue
  app/curriculum.py    SEEDED: Illuminate scenarios and Trial tasks
  tests/               pytest: Lock-In secrecy, debrief, confirmation, interventions, Trial leakage, voice fallback
```

Why a custom SVG graph rather than a graph library: the dim-to-lit transition needs control over every node and
edge, the layered layout is deterministic, and it keeps the bundle small.

## Checks run

| Check | Command | Result |
|---|---|---|
| Backend tests | `cd backend && uv run pytest` | 15 passed |
| Backend lint/format | `uv run ruff check . && uv run ruff format --check .` | clean |
| Backend types | `uv run mypy app` | no issues |
| Frontend lint | `cd frontend && npm run lint` | clean |
| Frontend types | `npm run typecheck` | clean |
| Frontend build | `npm run build` | success |
| End-to-end (Playwright, Chromium, no credentials) | Landing → Lock-In → debrief → teach-back → commit → map card → Illuminate L1 + L2 (€7,200 intervention) → tutor → Trial → reviewer; Live Coaching; offline state; 390px layout | all assertions passed |

## Verification checklist
- [x] App builds; tests, lint and type checks pass.
- [x] The full demo works with zero external credentials, through complete deterministic fallbacks.
- [x] Lock-In asks and reveals no questions before the session ends (server-enforced and tested).
- [x] The debrief asks ≥ 3 unanswered, contextual questions (5 in the sample) and ends in an expert-confirmable teach-back.
- [x] Expert-confirmed knowledge produces linked graph nodes and readable, evidence-backed skill cards.
- [x] Illuminate uses the graph, coaches, unlocks skills transparently, and catches the €7,200 opex mistake before submission.
- [x] Trial is visibly distinct, has no tutor, and gives reviewers evidence rather than a score or decision.

## Known limitations
- **Screen understanding is simulated in the demo.** Without a vision model, the sample session replays a scripted
  observation stream (labelled `SIMULATED`). With screen sharing alone, Umbra detects changes and pauses but can't
  tell what the work was; custom workflows then rely on expert notes and narration.
- The deterministic paraphraser mostly restates the expert's sentences in second person. An LLM produces more
  natural teach-backs. Hedge detection uses keyword cues and can miss subtle uncertainty, which is why every item
  still needs the expert's explicit confirmation.
- Illuminate scenarios and Trial tasks are authored seed content tied to node keys. Their explanations and
  citations come live from the confirmed graph, but generating new scenarios from an arbitrary graph is future work.
- Single demo learner; no user accounts. The reviewer console uses a shared access code, not real authentication.
- Voice and model paths are implemented against the public ElevenLabs, Anthropic and OpenAI APIs, but were tested
  here only through their "not configured" fallbacks; no keys were available in the build environment.
- SQLite with one process is fine for the MVP; production would need Postgres, auth and per-tenant isolation.
