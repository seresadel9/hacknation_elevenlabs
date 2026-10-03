export default function TrialLayout({ children }: { children: React.ReactNode }) {
  return (
    <div data-mode="trial" className="trial-shell">
      <div className="banner trial" role="note">
        <div className="container row-between">
          <span>◇ Assessment mode — no coaching, hints or feedback</span>
          <span className="tiny" style={{ textTransform: "none", letterSpacing: 0 }}>
            Evidence for human review only · no automated hiring decision
          </span>
        </div>
      </div>
      {children}
    </div>
  );
}
