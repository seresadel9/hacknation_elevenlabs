"use client";

import { useScribe, CommitStrategy } from "@elevenlabs/react";
import { useState } from "react";
import { post } from "@/lib/api";

/**
 * Optional: the expert narrates while working. Scribe v2 Realtime transcribes in the browser using a single-use
 * token minted by the backend (the API key never reaches the client). Committed segments are stored as expert
 * statements; "speaking" suppresses Live Coaching questions so Umbra never talks over the expert.
 */
export function VoiceNarration({
  sessionId,
  disabled,
  onSpeaking,
  onCommitted,
}: {
  sessionId: string;
  disabled: boolean;
  onSpeaking: (speaking: boolean) => void;
  onCommitted: () => void;
}) {
  const [error, setError] = useState<string | null>(null);
  const scribe = useScribe({
    modelId: "scribe_v2_realtime",
    commitStrategy: CommitStrategy.VAD,
    onPartialTranscript: (d) => onSpeaking(!!d.text),
    onCommittedTranscript: (d) => {
      onSpeaking(false);
      if (d.text.trim()) {
        post(`/sessions/${sessionId}/notes`, { text: d.text.trim(), kind: "transcript" })
          .then(onCommitted)
          .catch(() => {});
      }
    },
    onError: () => setError("Voice transcription stopped — notes still work."),
  });

  async function toggle() {
    setError(null);
    if (scribe.isConnected) {
      scribe.disconnect();
      onSpeaking(false);
      return;
    }
    try {
      const { token } = await post<{ token: string }>("/voice/scribe-token");
      await scribe.connect({ token, microphone: { echoCancellation: true, noiseSuppression: true } });
    } catch {
      setError("Microphone permission denied or voice service unavailable.");
    }
  }

  return (
    <div className="stack-sm">
      <button className={`btn sm ${scribe.isConnected ? "active" : ""}`} onClick={toggle} disabled={disabled}>
        {scribe.isConnected ? "● Narrating — stop" : "🎙 Narrate (Scribe v2 Realtime)"}
      </button>
      {scribe.partialTranscript && <span className="small faint mono">{scribe.partialTranscript}</span>}
      {error && <span className="small" style={{ color: "var(--danger)" }}>{error}</span>}
    </div>
  );
}
