export type NodeType = "skill" | "decision" | "guardrail" | "step" | "case" | "evidence";
export type NodeStatus = "draft" | "needs_confirmation" | "confirmed";
export type Provenance = "observed" | "expert_statement" | "ai_inference";

export interface Integrations {
  mode: "demo" | "live";
  elevenlabs: {
    configured: boolean;
    tts: boolean;
    stt: boolean;
    scribe_realtime: boolean;
    interviewer_agent: boolean;
    tutor_agent: boolean;
  };
  llm: { configured: boolean; provider: string | null };
  vision: { configured: boolean; provider: string | null };
}

export interface SessionEvent {
  id: string;
  t_s: number;
  clock: string;
  kind: string;
  source: "observed" | "expert" | "simulated" | "vision" | "system";
  activity: string | null;
  text: string;
  case: string | null;
  off_record: boolean;
}

export interface SessionState {
  id: string;
  workflow_name: string;
  mode: "lockin" | "live";
  status: "ready" | "active" | "paused" | "debrief" | "review" | "committed";
  seeded: boolean;
  speed: number;
  screen_share: boolean;
  work_time_s: number;
  clock: string;
  script_progress: number | null;
  script_complete: boolean;
  off_record: boolean;
  events: SessionEvent[];
  held_question_count: number;
  questions_asked_during_session: number;
  live_question: { id: string; text: string; gap_types: string[]; sample_answer: string | null; simulated: boolean } | null;
  live_answered: { id: string; text: string; answer: string | null; status: string }[];
  pacing_log: { t_s: number; clock: string; decision: string; reason: string }[];
}

export interface DebriefQuestion {
  id: string;
  key: string;
  text: string;
  gap_types: string[];
  priority: number;
  status: string;
  answer: string | null;
  phase: string | null;
  evidence: { clock: string; text: string; source: string } | null;
  sample_answer: string | null;
  generator: "model" | "deterministic";
}

export interface Debrief {
  session: { id: string; workflow_name: string; mode: "lockin" | "live"; status: SessionState["status"]; seeded: boolean };
  questions_asked_during_session: number;
  held_during_session: number;
  covered: { text: string; reason: string }[];
  answered_live: DebriefQuestion[];
  current: DebriefQuestion | null;
  progress: { asked: number; target: number; remaining: number };
  can_finish: boolean;
  answered: DebriefQuestion[];
  skipped: DebriefQuestion[];
  generator: string;
}

export interface TeachPart {
  field: string;
  text: string;
  quote: string | null;
  uncertain: boolean;
  node?: string;
  skill?: string;
}

export interface TeachSource {
  event_id?: string;
  question_id?: string;
  clock?: string;
  text: string;
  kind?: string;
  question?: string;
  phase?: string;
}

export interface TeachItem {
  id: string;
  seq: number;
  node_key: string;
  kind: "workflow" | "observed_decision" | "expert_answer" | "open_question";
  text: string;
  original_text: string;
  provenance: Provenance;
  generator: string;
  sources: TeachSource[];
  parts: TeachPart[];
  confidence: "high" | "medium" | "low";
  unresolved: string[];
  status: "pending" | "confirmed" | "edited" | "rejected";
  confirmable: boolean;
}

export interface Teachback {
  session: { id: string; workflow_name: string; status: string; mode: string; seeded: boolean };
  items: TeachItem[];
  generator: string;
}

export interface CardItem {
  text: string;
  quote?: string | null;
  provenance: Provenance;
  paraphrase_by?: string | null;
  confirmed: boolean;
  sources?: TeachSource[];
  via?: string;
}

export interface Card {
  meaning: { text: string; provenance: Provenance; confirmed: boolean } | null;
  when: { text: string; provenance: Provenance; confirmed: boolean } | null;
  how: CardItem[];
  why: CardItem[];
  thresholds: CardItem[];
  exceptions: CardItem[];
  escalation: CardItem[];
  never: CardItem[];
  observations: CardItem[];
  evidence: { event_id?: string; clock?: string; text: string; kind: string; simulated?: boolean; question?: string }[];
  open_questions: { text: string; reason: string }[];
}

export interface GraphNode {
  key: string;
  type: NodeType;
  title: string;
  summary: string;
  status: NodeStatus;
  card: Card;
  seeded: boolean;
  session_id: string | null;
  relations?: { type: string; direction: "in" | "out"; node: { key: string; type: NodeType; title: string; status: NodeStatus } }[];
}

export interface GraphEdge {
  id: number;
  src: string;
  dst: string;
  type: string;
  provenance: string;
}

export interface Graph {
  nodes: GraphNode[];
  edges: GraphEdge[];
  counts: Record<NodeStatus, number>;
}

export type LevelStatus = "awaiting_expert" | "locked" | "available" | "practiced" | "mastered";

export interface LevelState {
  id: string;
  order: number;
  title: string;
  subtitle: string;
  goal: string;
  skill: string;
  skill_title: string;
  status: LevelStatus;
  lock_reasons: string[];
  missing_confirmation: { key: string; title: string; status: string }[];
  missing_prereqs: { key: string; title: string }[];
  prereq_skills: string[];
  scenario_count: number;
  mastery_evidence: { rubric: Record<string, boolean>; attempts: string[]; decided_at: string } | null;
}

export interface InvoiceDocument {
  number: string;
  supplier: string;
  date: string;
  po: string;
  receipt: string;
  lines: [string, number, number][];
  net: number;
  notes: string[];
  prefilled_gl?: string;
}

export interface Option {
  id: string;
  label: string;
}

export interface Scenario {
  id: string;
  title: string;
  document: InvoiceDocument;
  prompt: string;
  actions: Option[];
  reasons: Option[];
}

export interface Citation {
  node: string;
  node_title: string;
  field: string;
  quote: string | null;
  text: string;
  clock: string | null;
}
