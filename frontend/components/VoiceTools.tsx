"use client";

import { ConversationProvider, useConversation } from "@elevenlabs/react";
import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { useIntegrations } from "./IntegrationsProvider";

/** Reads text aloud with ElevenLabs TTS (proxied by the backend). Renders nothing when TTS isn't configured. */
export function SpeakButton({ text, autoPlay = false }: { text: string; autoPlay?: boolean }) {
  const { integrations } = useIntegrations();
  const [state, setState] = useState<"idle" | "loading" | "playing" | "error">("idle");
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const enabled = !!integrations?.elevenlabs.tts;

  async function play() {
    if (!enabled) return;
    audioRef.current?.pause();
    setState("loading");
    try {
      const blob = await api<Blob>("/voice/tts", { method: "POST", json: { text } });
      const a = new Audio(URL.createObjectURL(blob));
      audioRef.current = a;
      a.onended = () => setState("idle");
      await a.play();
      setState("playing");
    } catch {
      setState("error");
    }
  }

  useEffect(() => {
    if (autoPlay && enabled) play();
    return () => audioRef.current?.pause();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- replay only when the text changes
  }, [text, enabled]);

  if (!enabled) return null;
  return (
    <button className="btn sm ghost" onClick={play} aria-label="Read aloud" title="Read aloud (ElevenLabs)">
      {state === "loading" ? "…" : state === "playing" ? "🔊 Playing" : state === "error" ? "Voice unavailable" : "🔊 Listen"}
    </button>
  );
}

/** Records an answer and transcribes it with ElevenLabs Speech-to-Text. Hidden when STT isn't configured. */
export function MicButton({ onText }: { onText: (text: string) => void }) {
  const { integrations } = useIntegrations();
  const [state, setState] = useState<"idle" | "recording" | "transcribing" | "denied" | "error">("idle");
  const recRef = useRef<MediaRecorder | null>(null);
  if (!integrations?.elevenlabs.stt) return null;

  async function toggle() {
    if (state === "recording") {
      recRef.current?.stop();
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const rec = new MediaRecorder(stream);
      const chunks: BlobPart[] = [];
      rec.ondataavailable = (e) => chunks.push(e.data);
      rec.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        setState("transcribing");
        const fd = new FormData();
        fd.append("file", new Blob(chunks, { type: rec.mimeType || "audio/webm" }), "answer.webm");
        try {
          const r = await fetch("/api/voice/stt", { method: "POST", body: fd });
          if (!r.ok) throw new Error();
          const { text } = await r.json();
          onText(text);
          setState("idle");
        } catch {
          setState("error");
        }
      };
      recRef.current = rec;
      rec.start();
      setState("recording");
    } catch {
      setState("denied");
    }
  }

  return (
    <button className={`btn sm ${state === "recording" ? "danger" : ""}`} onClick={toggle} type="button">
      {state === "recording" ? "■ Stop & transcribe" : state === "transcribing" ? "Transcribing…" : state === "denied" ? "Mic blocked — type instead" : state === "error" ? "Voice failed — type instead" : "🎙 Answer by voice"}
    </button>
  );
}

/**
 * ElevenAgents voice conversation (interviewer or tutor persona). Context is sent as a contextual update so the
 * agent stays grounded in Umbra's held questions / confirmed knowledge. Hidden unless the agent ID is configured.
 */
export function AgentPanel({ role, context, onUserMessage }: { role: "interviewer" | "tutor"; context: string; onUserMessage?: (t: string) => void }) {
  const { integrations } = useIntegrations();
  const enabled = role === "interviewer" ? integrations?.elevenlabs.interviewer_agent : integrations?.elevenlabs.tutor_agent;
  if (!enabled) return null;
  return (
    <ConversationProvider>
      <AgentInner role={role} context={context} onUserMessage={onUserMessage} />
    </ConversationProvider>
  );
}

function AgentInner({ role, context, onUserMessage }: { role: "interviewer" | "tutor"; context: string; onUserMessage?: (t: string) => void }) {
  const [error, setError] = useState<string | null>(null);
  const [lines, setLines] = useState<{ who: string; text: string }[]>([]);
  const conv = useConversation({
    onMessage: (m) => {
      setLines((l) => [...l.slice(-5), { who: m.source === "ai" ? "Umbra" : "You", text: m.message }]);
      if (m.source === "user") onUserMessage?.(m.message);
    },
    onError: () => setError("Voice conversation ended unexpectedly — text still works."),
  });
  const connected = conv.status === "connected";

  useEffect(() => {
    if (connected) conv.sendContextualUpdate(context);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- push context whenever it changes while connected
  }, [connected, context]);

  async function start() {
    setError(null);
    try {
      await navigator.mediaDevices.getUserMedia({ audio: true });
      const { signed_url } = await api<{ signed_url: string }>(`/voice/agent-url?role=${role}`);
      conv.startSession({ signedUrl: signed_url });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Microphone permission denied.");
    }
  }

  return (
    <div className="card tight stack-sm">
      <div className="row-between">
        <span className="small">
          <span className="tag accent">ElevenAgents</span> Voice {role === "interviewer" ? "debrief" : "tutor"}
        </span>
        {connected ? (
          <button className="btn sm danger" onClick={() => conv.endSession()}>
            End voice
          </button>
        ) : (
          <button className="btn sm" onClick={start}>
            Start voice {role === "interviewer" ? "debrief" : "tutor"}
          </button>
        )}
      </div>
      {connected && <span className="tiny faint">{conv.isSpeaking ? "Umbra is speaking…" : "Listening…"}</span>}
      {lines.map((l, i) => (
        <p key={i} className="small">
          <strong>{l.who}:</strong> <span className="muted">{l.text}</span>
        </p>
      ))}
      {error && <span className="small" style={{ color: "var(--danger)" }}>{error}</span>}
    </div>
  );
}
