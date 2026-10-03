"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Logo } from "./Logo";
import { useIntegrations } from "./IntegrationsProvider";

const STAGES = [
  { href: "/capture", label: "Capture", hint: "Learn in the quiet" },
  { href: "/map", label: "Map", hint: "Confirm what was learned" },
  { href: "/illuminate", label: "Illuminate", hint: "Master in the light" },
];

export function Header() {
  const path = usePathname() || "/";
  const { integrations } = useIntegrations();
  const isTrial = path.startsWith("/trial");
  return (
    <header className="site-header">
      <div className="container">
        <Link href="/" className="brand" aria-label="Umbra home">
          <Logo /> UMBRA
        </Link>
        <nav aria-label="Stages" className="stepper" style={isTrial ? { opacity: 0.55 } : undefined}>
          {STAGES.map((s, i) => (
            <span key={s.href} className="row" style={{ gap: 4 }}>
              {i > 0 && <span className="step-sep" aria-hidden="true" />}
              <Link
                href={s.href}
                className="step"
                aria-current={path.startsWith(s.href) ? "page" : undefined}
                title={s.hint}
              >
                <span className="num">{i + 1}</span>
                {s.label}
              </Link>
            </span>
          ))}
        </nav>
        <div className="header-right">
          {integrations && (
            <span
              className={`tag ${integrations.mode === "demo" ? "seed" : "accent"}`}
              title={
                integrations.mode === "demo"
                  ? "No external credentials configured — deterministic, clearly labelled demo fallbacks are used."
                  : "One or more external services are configured."
              }
            >
              {integrations.mode === "demo" ? "Demo mode · no keys" : "Live services"}
            </span>
          )}
          <Link href="/trial" className="trial-link" aria-current={isTrial ? "page" : undefined}>
            <span aria-hidden="true">◇</span> Trial <span className="sr-only">(separate recruiting assessment)</span>
          </Link>
        </div>
      </div>
    </header>
  );
}
