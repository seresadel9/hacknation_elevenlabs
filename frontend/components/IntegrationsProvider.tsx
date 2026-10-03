"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Integrations } from "@/lib/types";

interface Ctx {
  integrations: Integrations | null;
  online: boolean | null;
  refresh: () => void;
}

const IntegrationsContext = createContext<Ctx>({ integrations: null, online: null, refresh: () => {} });

export function IntegrationsProvider({ children }: { children: React.ReactNode }) {
  const [integrations, setIntegrations] = useState<Integrations | null>(null);
  const [online, setOnline] = useState<boolean | null>(null);

  const refresh = useCallback(() => {
    api<{ integrations: Integrations }>("/health")
      .then((h) => {
        setIntegrations(h.integrations);
        setOnline(true);
      })
      .catch(() => setOnline(false));
  }, []);

  useEffect(() => {
    refresh();
    const t = window.setInterval(refresh, 15000);
    const goOnline = () => refresh();
    const goOffline = () => setOnline(false);
    window.addEventListener("online", goOnline);
    window.addEventListener("offline", goOffline);
    return () => {
      window.clearInterval(t);
      window.removeEventListener("online", goOnline);
      window.removeEventListener("offline", goOffline);
    };
  }, [refresh]);

  return <IntegrationsContext.Provider value={{ integrations, online, refresh }}>{children}</IntegrationsContext.Provider>;
}

export const useIntegrations = () => useContext(IntegrationsContext);

export function OfflineBanner() {
  const { online, refresh } = useIntegrations();
  if (online !== false) return null;
  return (
    <div className="banner offline" role="alert">
      <div className="container row-between">
        <span>
          <strong>Umbra&apos;s backend is offline.</strong> Start it with{" "}
          <code>cd backend &amp;&amp; uv run uvicorn app.main:app --port 8000</code> — your work is saved in SQLite.
        </span>
        <button className="btn sm" onClick={refresh}>
          Retry
        </button>
      </div>
    </div>
  );
}
