"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { post } from "./api";

export type ShareState = "idle" | "requesting" | "sharing" | "denied" | "unsupported" | "ended";

const SAMPLE_MS = 2000;
const CHANGE_THRESHOLD = 0.06;
const IDLE_AFTER_MS = 20000;
const FRAME_UPLOAD_MIN_MS = 15000;

/**
 * Browser screen sharing with on-device change detection. Frames are downscaled and compared locally; nothing is
 * uploaded unless a vision model is configured, in which case an occasional small JPEG is sent, described, and
 * discarded server-side. A stable screen + no speech for 20 s is reported as a natural pause (used by Live Coaching).
 */
export function useScreenShare(sessionId: string, opts: { active: boolean; vision: boolean; speaking: boolean }) {
  const [state, setState] = useState<ShareState>("idle");
  const [lastChange, setLastChange] = useState<number | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const prevRef = useRef<Uint8ClampedArray | null>(null);
  const lastChangeRef = useRef<number>(0);
  const idleSentRef = useRef(false);
  const lastUploadRef = useRef(0);
  const optsRef = useRef(opts);
  useEffect(() => {
    optsRef.current = opts;
  }, [opts]);

  const stop = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    setState((s) => (s === "sharing" ? "ended" : s));
  }, []);

  const start = useCallback(async () => {
    if (!navigator.mediaDevices?.getDisplayMedia) {
      setState("unsupported");
      return;
    }
    setState("requesting");
    try {
      const stream = await navigator.mediaDevices.getDisplayMedia({ video: { frameRate: 2 }, audio: false });
      streamRef.current = stream;
      stream.getVideoTracks()[0]?.addEventListener("ended", () => {
        streamRef.current = null;
        setState("ended");
      });
      const v = document.createElement("video");
      v.muted = true;
      v.srcObject = stream;
      await v.play().catch(() => {});
      videoRef.current = v;
      lastChangeRef.current = Date.now();
      setState("sharing");
    } catch (e) {
      setState((e as DOMException)?.name === "NotAllowedError" ? "denied" : "unsupported");
    }
  }, []);

  useEffect(() => {
    if (state !== "sharing") return;
    const small = document.createElement("canvas");
    small.width = 64;
    small.height = 36;
    const sctx = small.getContext("2d", { willReadFrequently: true });
    const t = window.setInterval(() => {
      const v = videoRef.current;
      if (!v || !sctx || !optsRef.current.active) return;
      sctx.drawImage(v, 0, 0, small.width, small.height);
      const data = sctx.getImageData(0, 0, small.width, small.height).data;
      const gray = new Uint8ClampedArray(small.width * small.height);
      for (let i = 0; i < gray.length; i++) gray[i] = (data[i * 4] + data[i * 4 + 1] + data[i * 4 + 2]) / 3;
      const prev = prevRef.current;
      prevRef.current = gray;
      if (!prev) return;
      let diff = 0;
      for (let i = 0; i < gray.length; i++) diff += Math.abs(gray[i] - prev[i]);
      const score = diff / gray.length / 255;
      const now = Date.now();
      if (score > CHANGE_THRESHOLD) {
        lastChangeRef.current = now;
        idleSentRef.current = false;
        setLastChange(now);
        let frame: string | undefined;
        if (optsRef.current.vision && now - lastUploadRef.current > FRAME_UPLOAD_MIN_MS) {
          lastUploadRef.current = now;
          const big = document.createElement("canvas");
          big.width = 640;
          big.height = Math.round((640 * v.videoHeight) / Math.max(1, v.videoWidth));
          big.getContext("2d")?.drawImage(v, 0, 0, big.width, big.height);
          frame = big.toDataURL("image/jpeg", 0.6).split(",")[1];
        }
        post(`/sessions/${sessionId}/screen`, { kind: "change", score, frame_jpeg_b64: frame }).catch(() => {});
      } else if (!idleSentRef.current && !optsRef.current.speaking && now - lastChangeRef.current > IDLE_AFTER_MS) {
        idleSentRef.current = true;
        post(`/sessions/${sessionId}/screen`, { kind: "idle" }).catch(() => {});
      }
    }, SAMPLE_MS);
    return () => window.clearInterval(t);
  }, [state, sessionId]);

  useEffect(() => () => streamRef.current?.getTracks().forEach((t) => t.stop()), []);

  return { state, start, stop, lastChange };
}
