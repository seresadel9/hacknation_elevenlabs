import type { Metadata } from "next";
import "./globals.css";
import { Header } from "@/components/Header";
import { IntegrationsProvider, OfflineBanner } from "@/components/IntegrationsProvider";

export const metadata: Metadata = {
  title: "Umbra — Learn in the quiet. Master in the light.",
  description:
    "Umbra quietly learns how experienced people make decisions, turns it into an expert-confirmed skill graph, and lights it up for new hires.",
  icons: { icon: "/icon.svg" },
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        {/* eslint-disable-next-line @next/next/no-page-custom-font -- graceful fallback to system fonts offline */}
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&family=Space+Grotesk:wght@500;600&display=swap"
        />
      </head>
      <body>
        <a className="skip-link" href="#main">
          Skip to content
        </a>
        <IntegrationsProvider>
          <Header />
          <OfflineBanner />
          {children}
          <footer className="site-footer">
            <div className="container row-between">
              <span>
                Umbra · all people, companies, invoices and IBANs in the demo are fictional. Tags mark{" "}
                <span className="tag sim">Simulated</span> observations, <span className="tag seed">Seeded</span> demo data and{" "}
                <span className="tag inference">AI inference</span>.
              </span>
              <span>Hack-Nation × ElevenLabs · AI Apprentice</span>
            </div>
          </footer>
        </IntegrationsProvider>
      </body>
    </html>
  );
}
