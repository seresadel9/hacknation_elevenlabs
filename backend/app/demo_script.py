"""SEEDED DEMO DATA — the fictional invoice-processing session used when no screen/vision model is configured.

Everything here is fictional: "Mira" (24 years in Accounts Payable), Halden Logistics GmbH, every supplier,
invoice, IBAN and person. The script stands in for what a vision model would observe on a shared screen;
every event it produces is stored with source="simulated" and labelled as such in the UI.

Timestamps are in *work-clock seconds*. Seeded playback is compressed (see DEMO_SPEED) so a judge can watch a
ten-minute session in a little over a minute; the UI labels the compression.
"""

from __future__ import annotations

from typing import Any

DEMO_SCRIPT_NAME = "invoice_ap_mira"
DEMO_WORKFLOW_NAME = "Supplier invoice processing — Mira, Accounts Payable"
DEMO_EXPERT = "Mira (fictional) · 24 years in Accounts Payable"
DEMO_SPEED = 8.0

# --------------------------------------------------------------------------------------------------------------
# Observed session events (simulated screen understanding)
#   activity: what the expert appears to be doing — Live Coaching never interrupts unless it is "idle".
#   case:     invoice currently on screen (used for "only ask about what is visible").
#   refs:     work-map nodes this moment is evidence for.
#   gaps:     knowledge gaps this moment opens (resolved into questions by app.questions).
# --------------------------------------------------------------------------------------------------------------
SCRIPT_EVENTS: list[dict[str, Any]] = [
    {
        "key": "e01",
        "t": 4,
        "kind": "action",
        "activity": "navigating",
        "case": None,
        "text": "Opened the AP inbox — 5 new supplier invoices in today's batch",
        "refs": ["step-open-invoice"],
    },
    {
        "key": "e02",
        "t": 20,
        "kind": "action",
        "activity": "reading",
        "case": "INV-4471",
        "text": 'Opened INV-4471 · Quellwerk IT · €2,340.00 net (3× docking station, 3× 27" monitor)',
        "data": {"amount": 2340.0, "supplier": "Quellwerk IT"},
        "refs": ["case-inv-4471", "step-open-invoice"],
    },
    {
        "key": "e03",
        "t": 44,
        "kind": "action",
        "activity": "navigating",
        "case": "INV-4471",
        "text": "Three-way match: PO-88120 ✓ · goods receipt GR-5521 ✓ · quantities and prices agree",
        "refs": ["step-three-way-match", "s-three-way-match"],
    },
    {
        "key": "e04",
        "t": 62,
        "kind": "decision",
        "activity": "typing",
        "case": "INV-4471",
        "text": "Kept GL 6400 (Office equipment — opex) and approved INV-4471",
        "data": {"action": "approve", "gl": "6400", "amount": 2340.0},
        "refs": ["d-quellwerk-opex", "s-capex-classification", "step-gl-coding", "step-decide"],
    },
    {
        "key": "e05",
        "t": 76,
        "kind": "pause",
        "activity": "idle",
        "case": "INV-4471",
        "text": "Natural pause — no input for 9 s",
    },
    {
        "key": "e06",
        "t": 92,
        "kind": "action",
        "activity": "reading",
        "case": "INV-4472",
        "text": "Opened INV-4472 · Kessler Maschinenbau · €8,950.00 net — 1× semi-automatic pallet wrapper",
        "data": {"amount": 8950.0, "supplier": "Kessler Maschinenbau"},
        "refs": ["case-inv-4472"],
    },
    {
        "key": "e07",
        "t": 110,
        "kind": "action",
        "activity": "navigating",
        "case": "INV-4472",
        "text": "Three-way match: PO-88102 ✓ · goods receipt GR-5530 ✓",
        "refs": ["s-three-way-match"],
    },
    {
        "key": "e08",
        "t": 126,
        "kind": "decision",
        "activity": "typing",
        "case": "INV-4472",
        "text": "Changed GL 6400 → 0720 (Technical equipment — capitalised) and requested an asset tag",
        "data": {"action": "recode_capex", "gl_from": "6400", "gl_to": "0720", "amount": 8950.0},
        "refs": ["d-kessler-capex", "g-capex-5000", "s-capex-classification", "step-gl-coding"],
        "gaps": ["q-kessler-why", "q-capex-scope", "q-capex-boundary"],
    },
    {
        "key": "e09",
        "t": 141,
        "kind": "note",
        "activity": "speaking",
        "case": "INV-4472",
        "source": "expert",
        "text": "Anything that's a machine over five thousand goes on the balance sheet.",
        "refs": ["g-capex-5000"],
    },
    {
        "key": "e10",
        "t": 152,
        "kind": "pause",
        "activity": "idle",
        "case": "INV-4472",
        "text": "Natural pause — expert leaned back, no input for 12 s",
    },
    {
        "key": "e11",
        "t": 170,
        "kind": "action",
        "activity": "reading",
        "case": "INV-4473",
        "text": "Opened INV-4473 · Nordwind Bürobedarf · €612.40 net · invoice date 03 Dec",
        "data": {"amount": 612.40, "supplier": "Nordwind Bürobedarf"},
        "refs": ["case-inv-4473"],
    },
    {
        "key": "e12",
        "t": 186,
        "kind": "action",
        "activity": "navigating",
        "case": "INV-4473",
        "text": "Searched payment history: INV-4398 · Nordwind · €612.40 · paid 19 Nov",
        "refs": ["step-duplicate-check", "s-duplicate-detection"],
    },
    {
        "key": "e13",
        "t": 201,
        "kind": "decision",
        "activity": "typing",
        "case": "INV-4473",
        "text": 'Set INV-4473 to HOLD — reason: "possible duplicate, verify"',
        "data": {"action": "hold", "amount": 612.40},
        "refs": ["d-nordwind-hold", "g-nordwind-december", "s-duplicate-detection", "step-decide"],
        "gaps": ["q-nordwind-exception"],
    },
    {
        "key": "e14",
        "t": 212,
        "kind": "note",
        "activity": "speaking",
        "case": "INV-4473",
        "source": "expert",
        "text": "Nordwind again. Every December.",
        "refs": ["g-nordwind-december"],
    },
    {
        "key": "e15",
        "t": 226,
        "kind": "pause",
        "activity": "idle",
        "case": "INV-4473",
        "text": "Natural pause — no input for 8 s",
    },
    {
        "key": "e16",
        "t": 242,
        "kind": "action",
        "activity": "reading",
        "case": "INV-4474",
        "text": "Opened INV-4474 · Brightline Freight · €1,236.24 vs PO €1,212.00 (+2.0%)",
        "data": {"amount": 1236.24, "supplier": "Brightline Freight"},
        "refs": ["case-inv-4474"],
    },
    {
        "key": "e17",
        "t": 258,
        "kind": "action",
        "activity": "reading",
        "case": "INV-4474",
        "text": 'Cursor rested on "Reject variance" for 6 s, then returned to the invoice lines',
        "data": {"hesitation": True},
        "refs": ["s-variance-judgment"],
    },
    {
        "key": "e18",
        "t": 276,
        "kind": "decision",
        "activity": "typing",
        "case": "INV-4474",
        "text": 'Approved INV-4474 with variance note: "fuel surcharge, within tolerance"',
        "data": {"action": "approve_with_note", "amount": 1236.24},
        "refs": ["d-brightline-approve", "s-variance-judgment", "g-variance-tolerance", "step-decide"],
        "gaps": ["q-brightline-judgment"],
    },
    {
        "key": "e19",
        "t": 292,
        "kind": "pause",
        "activity": "idle",
        "case": "INV-4474",
        "text": "Natural pause — no input for 10 s",
    },
    {
        "key": "e20",
        "t": 310,
        "kind": "action",
        "activity": "reading",
        "case": "INV-4475",
        "text": 'Opened INV-4475 · Atlas Facility Services · €14,800.00 · "Please note our NEW bank details" · URGENT',
        "data": {"amount": 14800.0, "supplier": "Atlas Facility Services"},
        "refs": ["case-inv-4475"],
    },
    {
        "key": "e21",
        "t": 330,
        "kind": "action",
        "activity": "navigating",
        "case": "INV-4475",
        "text": "Opened Atlas vendor master — IBAN on file ends …4410; IBAN on invoice ends …9932",
        "refs": ["s-bank-change-escalation"],
    },
    {
        "key": "e22",
        "t": 346,
        "kind": "action",
        "activity": "navigating",
        "case": "INV-4475",
        "text": "Closed the vendor master without editing it",
        "data": {"hesitation": True},
        "refs": ["g-bank-details"],
    },
    {
        "key": "e23",
        "t": 362,
        "kind": "decision",
        "activity": "typing",
        "case": "INV-4475",
        "text": 'Forwarded INV-4475 to the Controller (J. Berg): "bank change on invoice, please verify" — status ESCALATED',
        "data": {"action": "escalate", "amount": 14800.0},
        "refs": ["d-atlas-escalate", "g-bank-details", "s-bank-change-escalation", "step-decide"],
        "gaps": ["q-atlas-never", "q-approval-limit"],
    },
    {
        "key": "e24",
        "t": 412,
        "kind": "pause",
        "activity": "idle",
        "case": "INV-4475",
        "text": "Natural pause — no input for 14 s",
    },
    {
        "key": "e25",
        "t": 428,
        "kind": "action",
        "activity": "navigating",
        "case": "INV-4473",
        "text": 'Returned to the hold queue; added to INV-4473: "call Nordwind AR"',
        "refs": ["d-nordwind-hold"],
    },
    {
        "key": "e26",
        "t": 446,
        "kind": "action",
        "activity": "navigating",
        "case": None,
        "text": "Submitted the batch: 3 approved · 1 on hold · 1 escalated",
        "refs": ["step-decide"],
    },
]

SCRIPT_END_T = 460.0

# --------------------------------------------------------------------------------------------------------------
# Gap catalogue: questions the apprentice can only answer by asking. Each is anchored to an observed moment.
#   gap_types drive prioritisation (risk) and coverage detection (has the expert already said it?).
# --------------------------------------------------------------------------------------------------------------
GAPS: dict[str, dict[str, Any]] = {
    "q-kessler-why": {
        "gap_types": ["why"],
        "text": "At {t} you recoded the Kessler pallet wrapper from opex (6400) to capex (0720). Why?",
        "live_text": "While it's on screen — why did the Kessler wrapper move from 6400 to 0720?",
        "targets": {"skill": "s-capex-classification", "node": "g-capex-5000"},
        "sample_answer": "Because it's a machine over €5,000, so it goes on the balance sheet.",
    },
    "q-capex-boundary": {
        "gap_types": ["threshold"],
        "text": (
            'At {t} you moved the €8,950 Kessler pallet wrapper to capex and said "{note}". '
            "Is that €5,000 line applied per item or to the invoice total — and is it net or gross of VAT?"
        ),
        "live_text": "Quick one while Kessler is on screen: is the €5,000 capex line per item or per invoice, net or gross?",
        "targets": {"skill": "s-capex-classification", "node": "g-capex-5000"},
        "sample_answer": (
            "Per item, net of VAT. If a single piece of equipment is €5,000 net or more, it is capex. "
            "Five laptops at €1,200 each on one invoice are still opex. "
            "If I'm unsure whether a bundle counts as one system, I ask Finance before coding it."
        ),
    },
    "q-capex-scope": {
        "gap_types": ["exception"],
        "text": (
            "Quellwerk's €2,340 of monitors stayed in opex at {t_other}, while Kessler's machine went to capex. "
            "Does the capex rule only apply to machinery, or to any equipment — and are there cases that behave differently?"
        ),
        "live_text": None,
        "other_event": "e04",
        "targets": {"skill": "s-capex-classification", "node": "g-capex-5000"},
        "sample_answer": (
            "Not only machinery — any single piece of equipment we will use for more than a year. "
            "Monitors are usually under the line per item. "
            "Honestly, software licences I'm not sure about — I'd check with Finance."
        ),
    },
    "q-nordwind-exception": {
        "gap_types": ["exception", "change_condition"],
        "text": (
            'At {t} you put Nordwind INV-4473 on hold and said "{note}". What happens with Nordwind in December, '
            "and what exactly would you need to see before releasing the hold?"
        ),
        "live_text": "Nordwind is on hold — what would you need to see before you release it?",
        "targets": {"skill": "s-duplicate-detection", "node": "g-nordwind-december"},
        "sample_answer": (
            "Nordwind's year-end billing run re-sends November invoices with new invoice numbers every December. "
            "I compare the amount and the delivery-note number against everything paid in the last 60 days. "
            "If the delivery note matches a paid invoice, it is a duplicate: never pay it, reject it and ask for a credit note. "
            "I only release a December Nordwind hold after Nordwind AR confirms in writing."
        ),
    },
    "q-brightline-judgment": {
        "gap_types": ["why", "change_condition"],
        "text": (
            'At {t} your cursor rested on "Reject variance" before you approved Brightline\'s +2.0% difference. '
            "What made this one acceptable — and what would have made you reject it?"
        ),
        "live_text": "Brightline's +2.0% — what made that acceptable, and what would make you reject it?",
        "targets": {"skill": "s-variance-judgment", "node": "g-variance-tolerance"},
        "sample_answer": (
            "Brightline's contract allows a fuel surcharge, so a small variance is expected. "
            "Up to 2.5% or €50, whichever is higher, I approve with a note. "
            "Above that, or if the supplier has no surcharge clause, I send it back to Purchasing."
        ),
    },
    "q-atlas-never": {
        "gap_types": ["never", "escalation"],
        "text": (
            "At {t} you opened Atlas's vendor master, closed it without editing, then escalated the €14,800 invoice. "
            "Is there anything an AP clerk must never do when an invoice announces new bank details — "
            "and is there any case where you would decide it yourself instead of escalating?"
        ),
        "live_text": "Atlas announced new bank details — what must a clerk never do here?",
        "targets": {"skill": "s-bank-change-escalation", "node": "g-bank-details"},
        "sample_answer": (
            "Never change bank details in the vendor master because an invoice or an email says so — that is the "
            "classic payment-fraud pattern. "
            "Bank changes always go to the Controller, who calls the supplier back on the number we already have on file. "
            "There is no case where I decide that myself. "
            "Urgency pressure on the invoice is a red flag on its own."
        ),
    },
    "q-approval-limit": {
        "gap_types": ["escalation"],
        "text": (
            "Even when the three-way match is clean, is there an amount above which you always ask someone before "
            "approving?"
        ),
        "live_text": None,
        "targets": {"skill": "s-three-way-match", "node": "s-three-way-match"},
        "sample_answer": (
            "Anything over €25,000 needs the Controller's second signature, even with a clean match. "
            "I never approve an invoice without a goods receipt."
        ),
    },
}

# Base risk weights per gap type: guardrails and escalation outrank "why".
GAP_WEIGHTS = {
    "never": 5.0,
    "escalation": 4.0,
    "threshold": 4.0,
    "exception": 3.6,
    "contradiction": 3.6,
    "change_condition": 3.0,
    "why": 2.0,
}

# --------------------------------------------------------------------------------------------------------------
# Work-map catalogue: what the (simulated) observer infers from the screen. Created as DRAFT nodes; only expert
# debrief answers + teach-back confirmation can light them up.
# --------------------------------------------------------------------------------------------------------------
NODE_CATALOG: dict[str, dict[str, Any]] = {
    # Workflow steps
    "step-open-invoice": {
        "type": "step",
        "title": "Open & read the invoice",
        "summary": "Review supplier, amount, lines and any notices before acting.",
    },
    "step-three-way-match": {
        "type": "step",
        "title": "Three-way match",
        "summary": "Compare invoice to purchase order and goods receipt.",
    },
    "step-gl-coding": {
        "type": "step",
        "title": "Assign the GL code",
        "summary": "Choose the general-ledger account: opex (6400) or capitalised equipment (0720).",
    },
    "step-duplicate-check": {
        "type": "step",
        "title": "Check for duplicates",
        "summary": "Search payment history for the same amount / delivery note.",
    },
    "step-decide": {
        "type": "step",
        "title": "Approve, hold or escalate",
        "summary": "Final disposition of the invoice in the batch.",
    },
    # Skills
    "s-three-way-match": {
        "type": "skill",
        "title": "Three-way match",
        "summary": "Confirm an invoice matches its purchase order and goods receipt before paying.",
        "meaning": "Check that what was ordered (PO), what arrived (goods receipt) and what is billed (invoice) agree.",
        "when": "Every supplier invoice that references a purchase order.",
        "how": [
            "Open the PO referenced on the invoice",
            "Open the goods receipt",
            "Compare quantities and unit prices",
        ],
    },
    "s-capex-classification": {
        "type": "skill",
        "title": "Capex vs opex classification",
        "summary": "Decide whether a purchase is an operating expense or a capitalised asset.",
        "meaning": "Code equipment that will be used long-term and is above the capitalisation line as an asset (0720).",
        "when": "Any invoice for equipment, machinery or hardware.",
        "how": [
            "Identify each piece of equipment on the invoice",
            "Compare each item to the capex line",
            "Recode 6400 → 0720 and request an asset tag when it applies",
        ],
    },
    "s-duplicate-detection": {
        "type": "skill",
        "title": "Duplicate billing detection",
        "summary": "Spot invoices that bill the same delivery twice.",
        "meaning": "Before paying, make sure the same goods have not already been paid under another invoice number.",
        "when": "Recurring suppliers, matching amounts, year-end billing runs.",
        "how": ["Search payment history for the same amount", "Compare delivery-note numbers", "Hold when in doubt"],
    },
    "s-variance-judgment": {
        "type": "skill",
        "title": "Price variance judgment",
        "summary": "Decide when a small difference between invoice and PO is acceptable.",
        "meaning": "Approve small, explainable variances; push back on unexplained ones.",
        "when": "Invoice total differs from the PO total.",
        "how": [
            "Compute the variance in % and €",
            "Check whether the contract explains it",
            "Approve with a note or return",
        ],
    },
    "s-bank-change-escalation": {
        "type": "skill",
        "title": "Escalate bank-detail changes",
        "summary": "Recognise payment-redirection risk and hand it to the Controller.",
        "meaning": "Treat any request to pay a different bank account as a fraud risk until independently verified.",
        "when": "An invoice or email announces new bank details or pushes for urgent payment.",
        "how": [
            "Compare the IBAN on the invoice with the vendor master",
            "Do not edit the vendor master",
            "Escalate to the Controller with the invoice attached",
        ],
    },
    # Guardrails
    "g-capex-5000": {
        "type": "guardrail",
        "title": "Equipment ≥ €5,000 net per item → capex",
        "summary": "Equipment above the capitalisation line is capex, not opex.",
    },
    "g-nordwind-december": {
        "type": "guardrail",
        "title": "Nordwind December duplicate-billing exception",
        "summary": "Hold December Nordwind invoices and verify against paid delivery notes.",
    },
    "g-bank-details": {
        "type": "guardrail",
        "title": "Never change bank details from an invoice",
        "summary": "Bank-detail changes are verified by the Controller via call-back.",
    },
    "g-variance-tolerance": {
        "type": "guardrail",
        "title": "Variance tolerance",
        "summary": "Small contractual variances may be approved with a note.",
    },
    # Decisions
    "d-quellwerk-opex": {
        "type": "decision",
        "title": "Quellwerk monitors kept in opex",
        "summary": "€2,340 of monitors and docks stayed on GL 6400.",
    },
    "d-kessler-capex": {
        "type": "decision",
        "title": "Kessler pallet wrapper recoded to capex",
        "summary": "€8,950 machine moved from 6400 to 0720 with an asset tag.",
    },
    "d-nordwind-hold": {
        "type": "decision",
        "title": "Nordwind INV-4473 held as possible duplicate",
        "summary": "Same amount as INV-4398, paid 19 Nov.",
    },
    "d-brightline-approve": {
        "type": "decision",
        "title": "Brightline +2.0% variance approved with note",
        "summary": "Judgment call — fuel surcharge within tolerance.",
    },
    "d-atlas-escalate": {
        "type": "decision",
        "title": "Atlas bank change escalated to Controller",
        "summary": "New IBAN on an urgent €14,800 invoice; vendor master not edited.",
    },
    # Cases
    "case-inv-4471": {"type": "case", "title": "INV-4471 · Quellwerk IT · €2,340", "summary": "Monitors and docks."},
    "case-inv-4472": {"type": "case", "title": "INV-4472 · Kessler · €8,950", "summary": "Pallet wrapping machine."},
    "case-inv-4473": {"type": "case", "title": "INV-4473 · Nordwind · €612.40", "summary": "December office supplies."},
    "case-inv-4474": {"type": "case", "title": "INV-4474 · Brightline · €1,236.24", "summary": "Freight, +2.0% vs PO."},
    "case-inv-4475": {"type": "case", "title": "INV-4475 · Atlas · €14,800", "summary": "New bank details, urgent."},
}

EDGE_CATALOG: list[tuple[str, str, str]] = [
    ("step-open-invoice", "step-three-way-match", "prerequisite_for"),
    ("step-three-way-match", "step-gl-coding", "prerequisite_for"),
    ("step-three-way-match", "step-duplicate-check", "prerequisite_for"),
    ("step-gl-coding", "step-decide", "prerequisite_for"),
    ("step-duplicate-check", "step-decide", "prerequisite_for"),
    ("s-three-way-match", "s-capex-classification", "prerequisite_for"),
    ("s-three-way-match", "s-duplicate-detection", "prerequisite_for"),
    ("s-three-way-match", "s-variance-judgment", "prerequisite_for"),
    ("s-duplicate-detection", "s-bank-change-escalation", "prerequisite_for"),
    ("s-capex-classification", "s-bank-change-escalation", "prerequisite_for"),
    ("s-capex-classification", "step-gl-coding", "depends_on"),
    ("s-three-way-match", "step-three-way-match", "depends_on"),
    ("s-duplicate-detection", "step-duplicate-check", "depends_on"),
    ("s-capex-classification", "g-capex-5000", "constrained_by"),
    ("s-duplicate-detection", "g-nordwind-december", "constrained_by"),
    ("g-nordwind-december", "s-duplicate-detection", "exception_to"),
    ("s-bank-change-escalation", "g-bank-details", "constrained_by"),
    ("s-variance-judgment", "g-variance-tolerance", "constrained_by"),
    ("s-capex-classification", "d-kessler-capex", "demonstrated_by"),
    ("s-capex-classification", "d-quellwerk-opex", "demonstrated_by"),
    ("s-three-way-match", "d-quellwerk-opex", "demonstrated_by"),
    ("s-duplicate-detection", "d-nordwind-hold", "demonstrated_by"),
    ("s-variance-judgment", "d-brightline-approve", "demonstrated_by"),
    ("s-bank-change-escalation", "d-atlas-escalate", "demonstrated_by"),
    ("d-quellwerk-opex", "case-inv-4471", "demonstrated_by"),
    ("d-kessler-capex", "case-inv-4472", "demonstrated_by"),
    ("d-nordwind-hold", "case-inv-4473", "demonstrated_by"),
    ("d-brightline-approve", "case-inv-4474", "demonstrated_by"),
    ("d-atlas-escalate", "case-inv-4475", "demonstrated_by"),
]

# Observed-decision teach-back: what the apprentice *infers* from watching. Always labelled as inference.
DECISION_INFERENCES: dict[str, dict[str, str]] = {
    "d-quellwerk-opex": {
        "skill": "s-three-way-match",
        "text": "I saw you confirm the PO and goods receipt before approving anything — so I never approve an "
        "invoice until the three-way match is clean.",
    },
    "d-kessler-capex": {
        "skill": "s-capex-classification",
        "text": "I saw you move a machine invoice from 6400 to 0720 and request an asset tag — so large equipment "
        "is recoded to capex before approval, not left in opex.",
    },
    "d-nordwind-hold": {
        "skill": "s-duplicate-detection",
        "text": "I saw you search payment history and hold an invoice whose amount matched one already paid — so a "
        "matching amount is a reason to hold, not to pay.",
    },
    "d-brightline-approve": {
        "skill": "s-variance-judgment",
        "text": "I saw you hesitate on a +2.0% variance and then approve it with a note — so small explained "
        "variances are approved, but always documented.",
    },
    "d-atlas-escalate": {
        "skill": "s-bank-change-escalation",
        "text": "I saw you look at the vendor master, change nothing, and escalate — so when bank details change, "
        "I escalate instead of editing anything myself.",
    },
}
