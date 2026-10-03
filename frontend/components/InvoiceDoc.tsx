import type { InvoiceDocument } from "@/lib/types";
import { eur } from "./ui";

export function InvoiceDoc({ doc, glOverride }: { doc: InvoiceDocument; glOverride?: string }) {
  return (
    <div className="invoice" role="document" aria-label={`Invoice ${doc.number} from ${doc.supplier}`}>
      <div className="inv-head">
        <div>
          <div style={{ fontWeight: 600, fontSize: 15 }}>{doc.supplier}</div>
          <div className="inv-no">{doc.number} · {doc.date}</div>
        </div>
        <div style={{ textAlign: "right" }}>
          <div className="inv-no">Bill to: Halden Logistics GmbH</div>
          <div className="inv-no">(fictional)</div>
        </div>
      </div>
      <table>
        <thead>
          <tr>
            <th>Description</th>
            <th className="num">Qty</th>
            <th className="num">Unit (net)</th>
            <th className="num">Net</th>
          </tr>
        </thead>
        <tbody>
          {doc.lines.map(([d, q, u], i) => (
            <tr key={i}>
              <td>{d}</td>
              <td className="num">{q}</td>
              <td className="num">{eur(u)}</td>
              <td className="num">{eur(q * u)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="total">
        <span>Total net</span>
        <span>{eur(doc.net)}</span>
      </div>
      <div className="inv-meta">
        <span>{doc.po}</span>
        <span>{doc.receipt}</span>
      </div>
      {doc.prefilled_gl && (
        <div className="gl-chip">
          GL {glOverride ?? doc.prefilled_gl} {glOverride && glOverride !== doc.prefilled_gl ? "· recoded" : "· auto-coded by OCR"}
        </div>
      )}
      {doc.notes.map((n, i) => (
        <div key={i} className="inv-note">{n}</div>
      ))}
    </div>
  );
}
