"""SEEDED DEMO DATA — practice scenarios (Illuminate) and assessment tasks (Trial). All fictional.

Scenarios are authored against Work Map node keys. A level only opens once the guardrails it teaches are
expert-confirmed, and every explanation the tutor gives is pulled live from those confirmed cards.
"""

from __future__ import annotations

from typing import Any

LEVELS: list[dict[str, Any]] = [
    {
        "id": "L1",
        "order": 1,
        "title": "First light",
        "subtitle": "Three-way match",
        "skill": "s-three-way-match",
        "requires_confirmed": ["s-three-way-match"],
        "prereq_skills": [],
        "goal": "Never pay for something that has not been ordered and received.",
        "scenarios": ["sc-1a", "sc-1b"],
    },
    {
        "id": "L2",
        "order": 2,
        "title": "Capex or opex",
        "subtitle": "Capitalisation guardrail",
        "skill": "s-capex-classification",
        "requires_confirmed": ["g-capex-5000"],
        "prereq_skills": ["s-three-way-match"],
        "goal": "Put equipment on the balance sheet when the expert's rule says so — and only then.",
        "scenarios": ["sc-2a", "sc-2b"],
    },
    {
        "id": "L3",
        "order": 3,
        "title": "December echoes",
        "subtitle": "Duplicate billing",
        "skill": "s-duplicate-detection",
        "requires_confirmed": ["g-nordwind-december"],
        "prereq_skills": ["s-three-way-match"],
        "goal": "Catch invoices that bill the same delivery twice, including Nordwind's year-end run.",
        "scenarios": ["sc-3a", "sc-3b"],
    },
    {
        "id": "L4",
        "order": 4,
        "title": "Judgment call",
        "subtitle": "Price variance",
        "skill": "s-variance-judgment",
        "requires_confirmed": ["g-variance-tolerance"],
        "prereq_skills": ["s-three-way-match"],
        "goal": "Approve small, explained differences; push back on the rest.",
        "scenarios": ["sc-4a", "sc-4b"],
    },
    {
        "id": "L5",
        "order": 5,
        "title": "Stop and escalate",
        "subtitle": "Bank-detail changes",
        "skill": "s-bank-change-escalation",
        "requires_confirmed": ["g-bank-details"],
        "prereq_skills": ["s-capex-classification", "s-duplicate-detection"],
        "goal": "Recognise payment-redirection risk and hand it to the right person.",
        "scenarios": ["sc-5a", "sc-5b"],
    },
]

RUBRIC = [
    {"id": "action", "label": "Chooses the expert's action on every case"},
    {"id": "reason", "label": "Gives the reason the expert would give"},
    {"id": "guardrails", "label": "Misses no guardrail at submission"},
    {"id": "independent", "label": "Solves at least one case without the tutor stepping in"},
]

SCENARIOS: dict[str, dict[str, Any]] = {
    "sc-1a": {
        "level": "L1",
        "title": "Keyboards, no receipt yet",
        "document": {
            "number": "INV-5102",
            "supplier": "Quellwerk IT",
            "date": "14 Jan",
            "po": "PO-88311 ✓",
            "receipt": "Goods receipt: not posted",
            "lines": [["Wireless keyboard + mouse set", 10, 118.00]],
            "net": 1180.00,
            "notes": ['Warehouse note: "delivery expected Friday"'],
        },
        "prompt": "The PO matches. What do you do with this invoice today?",
        "actions": [
            {"id": "approve", "label": "Approve — the PO matches"},
            {"id": "hold-gr", "label": "Hold until the goods receipt is posted"},
            {"id": "reject", "label": "Reject the invoice"},
            {"id": "escalate", "label": "Escalate to the Controller"},
        ],
        "correct_action": "hold-gr",
        "reasons": [
            {"id": "small", "label": "It's a small amount, so it's low risk either way"},
            {"id": "no-gr", "label": "Without a goods receipt, delivery isn't confirmed — the match isn't complete"},
            {"id": "supplier", "label": "Quellwerk is a new supplier"},
        ],
        "correct_reason": "no-gr",
        "consequential": {
            "approve": {
                "node": "s-three-way-match",
                "cite": ["goods receipt", "three-way", "match", "never approve"],
                "lead": "Before you submit — the goods receipt for INV-5102 hasn't been posted, so only two of the three documents agree.",
            }
        },
        "tutor_prompt": "Which three documents have to agree — and how many of them can you actually see here?",
        "explain": "Mira only approves when PO, goods receipt and invoice all agree. Hold it until the receipt is posted.",
    },
    "sc-1b": {
        "level": "L1",
        "title": "A clean match",
        "document": {
            "number": "INV-5110",
            "supplier": "Fresh & Co Catering",
            "date": "15 Jan",
            "po": "PO-88340 ✓",
            "receipt": "Goods receipt GR-5702 ✓",
            "lines": [["Canteen supplies, week 2", 1, 420.00]],
            "net": 420.00,
            "notes": [],
        },
        "prompt": "Everything is posted. What do you do?",
        "actions": [
            {"id": "approve", "label": "Approve"},
            {"id": "hold", "label": "Hold for a second check"},
            {"id": "escalate", "label": "Escalate to the Controller"},
        ],
        "correct_action": "approve",
        "reasons": [
            {"id": "match", "label": "PO, goods receipt and invoice agree"},
            {"id": "amount", "label": "It's under €500"},
            {"id": "habit", "label": "We always pay this supplier"},
        ],
        "correct_reason": "match",
        "consequential": {},
        "tutor_prompt": "What would have to be missing for you to hold this one?",
        "explain": "All three documents agree — this is exactly the case Mira approves without further checks.",
    },
    "sc-2a": {
        "level": "L2",
        "title": "The €7,200 label printer",
        "document": {
            "number": "INV-5120",
            "supplier": "Kessler Maschinenbau",
            "date": "16 Jan",
            "po": "PO-88355 ✓",
            "receipt": "Goods receipt GR-5711 ✓",
            "lines": [["Industrial label printer system (1 unit)", 1, 7200.00]],
            "net": 7200.00,
            "notes": ["Auto-coded by the inbox OCR: GL 6400 · Office equipment (opex)"],
            "prefilled_gl": "6400",
        },
        "prompt": "The invoice arrived pre-coded to GL 6400 (opex). What do you submit?",
        "actions": [
            {"id": "approve-6400", "label": "Approve as coded — GL 6400 (opex)"},
            {"id": "recode-0720", "label": "Recode to GL 0720 (capex), request an asset tag, then approve"},
            {"id": "hold", "label": "Hold and ask the supplier for a breakdown"},
            {"id": "escalate", "label": "Escalate to the Controller"},
        ],
        "correct_action": "recode-0720",
        "reasons": [
            {"id": "under-10k", "label": "It's under €10,000, so opex is fine"},
            {"id": "per-item", "label": "One piece of equipment at €5,000 net or more is capex"},
            {"id": "buildings", "label": "Capex is only for buildings and vehicles"},
        ],
        "correct_reason": "per-item",
        "consequential": {
            "approve-6400": {
                "node": "g-capex-5000",
                "cite": ["5,000", "per item", "net", "capex", "single piece"],
                "lead": "Hold on — before you submit. This is one €7,200 net piece of equipment, and it is still coded to "
                "6400 (opex).",
            }
        },
        "tutor_prompt": "How many items are on this invoice, and what is the net price of each one?",
        "explain": "A single €7,200 net printer system is above Mira's €5,000-per-item line, so it is capitalised (0720) "
        "with an asset tag — the OCR's opex coding is wrong.",
    },
    "sc-2b": {
        "level": "L2",
        "title": "Five laptops",
        "document": {
            "number": "INV-5124",
            "supplier": "Quellwerk IT",
            "date": "17 Jan",
            "po": "PO-88362 ✓",
            "receipt": "Goods receipt GR-5720 ✓",
            "lines": [['Laptop 14" (standard build)', 5, 1200.00]],
            "net": 6000.00,
            "notes": ["Auto-coded by the inbox OCR: GL 6400 · Office equipment (opex)"],
            "prefilled_gl": "6400",
        },
        "prompt": "The total is €6,000 net. What do you submit?",
        "actions": [
            {"id": "approve-6400", "label": "Approve as coded — GL 6400 (opex)"},
            {"id": "recode-0720", "label": "Recode to GL 0720 (capex), then approve"},
            {"id": "escalate", "label": "Escalate to the Controller"},
        ],
        "correct_action": "approve-6400",
        "reasons": [
            {"id": "total", "label": "The invoice total is over €5,000, so it's capex"},
            {"id": "per-item", "label": "Each laptop is €1,200 — the line applies per item, not per invoice"},
            {"id": "laptops", "label": "Laptops are never capex"},
        ],
        "correct_reason": "per-item",
        "consequential": {
            "recode-0720": {
                "node": "g-capex-5000",
                "cite": ["per item", "laptops", "invoice", "opex"],
                "lead": "Before you submit — the total is over €5,000, but look at what each item costs.",
            }
        },
        "tutor_prompt": "Does the capex line apply to the invoice total or to each item?",
        "explain": "The line is per item, net. Five €1,200 laptops stay in opex even though the invoice total is €6,000.",
    },
    "sc-3a": {
        "level": "L3",
        "title": "Same delivery note",
        "document": {
            "number": "INV-5131",
            "supplier": "Nordwind Bürobedarf",
            "date": "05 Dec",
            "po": "PO-88021 ✓",
            "receipt": "Delivery note DN-6604",
            "lines": [["Copy paper A4, 40 boxes", 1, 248.90]],
            "net": 248.90,
            "notes": ["Payment history: INV-5019 · €248.90 · delivery note DN-6604 · paid 21 Nov"],
        },
        "prompt": "What do you do with INV-5131?",
        "actions": [
            {"id": "approve", "label": "Approve — the PO and receipt match"},
            {"id": "hold", "label": "Hold and wait"},
            {"id": "reject-credit", "label": "Reject as a duplicate and ask Nordwind for a credit note"},
            {"id": "escalate", "label": "Escalate to the Controller"},
        ],
        "correct_action": "reject-credit",
        "reasons": [
            {"id": "same-dn", "label": "The delivery note matches an invoice already paid — it's a duplicate"},
            {"id": "december", "label": "All December invoices are rejected"},
            {"id": "amount", "label": "The amount is too high for paper"},
        ],
        "correct_reason": "same-dn",
        "consequential": {
            "approve": {
                "node": "g-nordwind-december",
                "cite": ["delivery-note", "delivery note", "duplicate", "never pay", "credit note"],
                "lead": "Wait — before you submit. Compare the delivery note on this invoice with the payment history.",
            }
        },
        "tutor_prompt": "What does the payment history tell you about delivery note DN-6604?",
        "explain": "DN-6604 was already paid on INV-5019. Mira's rule: a matching delivery note means a duplicate — never "
        "pay it, reject it and ask for a credit note.",
    },
    "sc-3b": {
        "level": "L3",
        "title": "No match, still December",
        "document": {
            "number": "INV-5135",
            "supplier": "Nordwind Bürobedarf",
            "date": "09 Dec",
            "po": "PO-88044 ✓",
            "receipt": "Delivery note DN-6721",
            "lines": [["Toner cartridges", 2, 48.20]],
            "net": 96.40,
            "notes": ["Payment history (60 days): no invoice with DN-6721 or €96.40"],
        },
        "prompt": "No matching delivery note. What do you do?",
        "actions": [
            {"id": "approve", "label": "Approve — nothing matches, so it isn't a duplicate"},
            {"id": "hold-ar", "label": "Hold until Nordwind AR confirms in writing"},
            {"id": "reject-credit", "label": "Reject and ask for a credit note"},
        ],
        "correct_action": "hold-ar",
        "reasons": [
            {"id": "written", "label": "December Nordwind holds are only released after written AR confirmation"},
            {"id": "small", "label": "It's too small to matter"},
            {"id": "dup", "label": "It is a duplicate"},
        ],
        "correct_reason": "written",
        "consequential": {
            "approve": {
                "node": "g-nordwind-december",
                "cite": ["release", "AR confirms", "writing", "December"],
                "lead": "Before you submit — this is a December Nordwind invoice.",
            }
        },
        "tutor_prompt": "What did Mira say has to happen before a December Nordwind hold is released?",
        "explain": "Even without a match, Mira only releases December Nordwind invoices once Nordwind AR confirms in writing.",
    },
    "sc-4a": {
        "level": "L4",
        "title": "A small surcharge",
        "document": {
            "number": "INV-5140",
            "supplier": "Brightline Freight",
            "date": "20 Jan",
            "po": "PO-88390 · €820.00",
            "receipt": "Goods receipt GR-5744 ✓",
            "lines": [["Freight Hamburg → Leipzig", 1, 820.00], ["Fuel surcharge", 1, 22.10]],
            "net": 842.10,
            "notes": ["Variance vs PO: +€22.10 (+2.7%) · contract has a fuel-surcharge clause"],
        },
        "prompt": "+2.7% over the PO. What do you do?",
        "actions": [
            {"id": "approve-note", "label": "Approve with a variance note"},
            {"id": "return", "label": "Send back to Purchasing"},
            {"id": "approve-silent", "label": "Approve without a note"},
        ],
        "correct_action": "approve-note",
        "reasons": [
            {
                "id": "tolerance",
                "label": "€22 is under the €50 floor of the tolerance (2.5% or €50, whichever is higher)",
            },
            {"id": "pct", "label": "Anything over 2.5% must go back"},
            {"id": "freight", "label": "Freight is always approved"},
        ],
        "correct_reason": "tolerance",
        "consequential": {
            "approve-silent": {
                "node": "g-variance-tolerance",
                "cite": ["note", "approve", "2.5%", "€50"],
                "lead": "Almost — before you submit, how would the next person know why this variance was accepted?",
            }
        },
        "tutor_prompt": "Is the tolerance a percentage, an amount — or whichever is higher?",
        "explain": "The tolerance is 2.5% or €50, whichever is higher. €22.10 is within €50, and the contract allows a "
        "surcharge — approve, and document it with a note.",
    },
    "sc-4b": {
        "level": "L4",
        "title": "No surcharge clause",
        "document": {
            "number": "INV-5144",
            "supplier": "Kranich Verpackung",
            "date": "21 Jan",
            "po": "PO-88402 · €3,250.00",
            "receipt": "Goods receipt GR-5751 ✓",
            "lines": [["Carton boxes, mixed", 1, 3390.00]],
            "net": 3390.00,
            "notes": ["Variance vs PO: +€140.00 (+4.3%) · no surcharge clause in the contract"],
        },
        "prompt": "+€140 over the PO. What do you do?",
        "actions": [
            {"id": "approve-note", "label": "Approve with a variance note"},
            {"id": "return", "label": "Send back to Purchasing"},
            {"id": "escalate", "label": "Escalate to the Controller"},
        ],
        "correct_action": "return",
        "reasons": [
            {"id": "over", "label": "It's above both 2.5% and €50, and there's no surcharge clause"},
            {"id": "supplier", "label": "Kranich is unreliable"},
            {"id": "always", "label": "Every variance goes back to Purchasing"},
        ],
        "correct_reason": "over",
        "consequential": {
            "approve-note": {
                "node": "g-variance-tolerance",
                "cite": ["above that", "Purchasing", "no surcharge clause"],
                "lead": "Before you submit — check this variance against the tolerance and the contract.",
            }
        },
        "tutor_prompt": "Is +€140 / +4.3% inside the tolerance — and does the contract explain it?",
        "explain": "€140 / 4.3% exceeds both the €50 and the 2.5% line, and there is no surcharge clause: send it back to "
        "Purchasing.",
    },
    "sc-5a": {
        "level": "L5",
        "title": '"Please update our bank details"',
        "document": {
            "number": "INV-5150",
            "supplier": "Quellwerk IT",
            "date": "22 Jan",
            "po": "PO-88410 ✓",
            "receipt": "Goods receipt GR-5760 ✓",
            "lines": [["Network switches", 6, 3150.00]],
            "net": 18900.00,
            "notes": [
                'Email from accounts@quellwerk-it-billing.com: "Our bank has changed. Please update the IBAN to '
                '…7781 and pay today to avoid a supply stop."'
            ],
        },
        "prompt": "The email asks you to update the IBAN and pay today. What do you do?",
        "actions": [
            {"id": "update-pay", "label": "Update the IBAN in the vendor master and pay"},
            {"id": "reply", "label": "Reply to the email to confirm the new IBAN"},
            {"id": "escalate", "label": "Escalate to the Controller — don't edit anything"},
            {"id": "hold-quiet", "label": "Put it on hold and wait for the supplier to call"},
        ],
        "correct_action": "escalate",
        "reasons": [
            {"id": "fraud", "label": "Bank changes are verified by the Controller via call-back to the number on file"},
            {"id": "amount", "label": "€18,900 is too much to pay without approval"},
            {"id": "email", "label": "Emails are never read by AP"},
        ],
        "correct_reason": "fraud",
        "consequential": {
            "update-pay": {
                "node": "g-bank-details",
                "cite": ["never change bank details", "Controller", "calls the supplier back"],
                "lead": "Stop — before you submit. This would change bank details because an email asked you to.",
            },
            "reply": {
                "node": "g-bank-details",
                "cite": ["number we already have on file", "Controller", "never"],
                "lead": "Careful — replying to that email confirms nothing: you'd be asking the sender to vouch for themselves.",
            },
        },
        "tutor_prompt": "Who verifies a bank change at Halden, and which phone number do they use?",
        "explain": "Never change bank details because an invoice or email says so. The Controller verifies via call-back "
        "on the number already on file. Urgency is a red flag by itself.",
    },
    "sc-5b": {
        "level": "L5",
        "title": "Nothing changed",
        "document": {
            "number": "INV-5156",
            "supplier": "Atlas Facility Services",
            "date": "23 Jan",
            "po": "PO-88415 ✓",
            "receipt": "Service entry SE-1190 ✓",
            "lines": [["Office cleaning, January", 1, 2450.00]],
            "net": 2450.00,
            "notes": ["IBAN on invoice …4410 — same as vendor master"],
        },
        "prompt": "What do you do?",
        "actions": [
            {"id": "approve", "label": "Approve"},
            {"id": "escalate", "label": "Escalate to the Controller to be safe"},
            {"id": "hold", "label": "Hold and call Atlas"},
        ],
        "correct_action": "approve",
        "reasons": [
            {"id": "same", "label": "The bank details match the vendor master and the match is clean"},
            {"id": "atlas", "label": "Atlas is a trusted supplier"},
            {"id": "small", "label": "It's under €5,000"},
        ],
        "correct_reason": "same",
        "consequential": {},
        "tutor_prompt": "What exactly would make this invoice need escalating — is any of it present?",
        "explain": "Escalation is for bank-detail changes and urgency pressure. Nothing changed here and the match is "
        "clean, so approve.",
    },
}

# --------------------------------------------------------------------------------------------------------------
# Trial (recruiting assessment). Expected answers and cue words are reviewer-only — never sent to candidates.
# --------------------------------------------------------------------------------------------------------------
TRIAL_TASKS: list[dict[str, Any]] = [
    {
        "id": "T1",
        "skill": "s-capex-classification",
        "title": "Server for the warehouse",
        "document": {
            "number": "INV-T201",
            "supplier": "Quellwerk IT",
            "date": "02 Feb",
            "po": "PO-89001 ✓",
            "receipt": "Goods receipt GR-6010 ✓",
            "lines": [["Rack server, 2U (1 unit)", 1, 12400.00]],
            "net": 12400.00,
            "notes": ["Auto-coded by the inbox OCR: GL 6400 · Office equipment (opex)"],
        },
        "actions": [
            {"id": "approve-6400", "label": "Approve on GL 6400 (opex)"},
            {"id": "recode-0720", "label": "Recode to GL 0720 (capex) with an asset tag, then approve"},
            {"id": "hold", "label": "Hold"},
            {"id": "escalate", "label": "Escalate to the Controller"},
        ],
        "expected_action": "recode-0720",
        "cues": ["5,000", "5000", "per item", "capex", "asset", "balance sheet", "capital", "net"],
    },
    {
        "id": "T2",
        "skill": "s-duplicate-detection",
        "title": "December office supplies",
        "document": {
            "number": "INV-T202",
            "supplier": "Nordwind Bürobedarf",
            "date": "12 Dec",
            "po": "PO-88980 ✓",
            "receipt": "Delivery note DN-7781",
            "lines": [["Office chairs, task", 4, 128.00]],
            "net": 512.00,
            "notes": ["Payment history: INV-T150 · €512.00 · delivery note DN-7781 · paid 28 Nov"],
        },
        "actions": [
            {"id": "approve", "label": "Approve"},
            {"id": "hold", "label": "Hold"},
            {"id": "reject-credit", "label": "Reject and request a credit note"},
            {"id": "escalate", "label": "Escalate to the Controller"},
        ],
        "expected_action": "reject-credit",
        "cues": ["delivery note", "dn-7781", "duplicate", "already paid", "credit note", "december"],
    },
    {
        "id": "T3",
        "skill": "s-bank-change-escalation",
        "title": "Urgent payment request",
        "document": {
            "number": "INV-T203",
            "supplier": "Kessler Maschinenbau",
            "date": "03 Feb",
            "po": "PO-89012 ✓",
            "receipt": "Goods receipt GR-6022 ✓",
            "lines": [["Conveyor module", 1, 23100.00]],
            "net": 23100.00,
            "notes": ['Email: "Due to an audit our IBAN changed to …0456. Please update your records and pay today."'],
        },
        "actions": [
            {"id": "update-pay", "label": "Update the IBAN and pay"},
            {"id": "reply", "label": "Reply to the email to confirm"},
            {"id": "escalate", "label": "Escalate to the Controller without editing anything"},
            {"id": "approve", "label": "Approve to the existing IBAN"},
        ],
        "expected_action": "escalate",
        "cues": ["controller", "call back", "call-back", "on file", "fraud", "never", "verify", "urgent"],
    },
    {
        "id": "T4",
        "skill": "s-variance-judgment",
        "title": "Freight over PO",
        "document": {
            "number": "INV-T204",
            "supplier": "Brightline Freight",
            "date": "04 Feb",
            "po": "PO-89020 · €1,450.00",
            "receipt": "Goods receipt GR-6031 ✓",
            "lines": [["Freight Bremen → Dresden", 1, 1450.00], ["Fuel surcharge", 1, 80.00]],
            "net": 1530.00,
            "notes": ["Variance vs PO: +€80.00 (+5.5%)"],
        },
        "actions": [
            {"id": "approve-note", "label": "Approve with a variance note"},
            {"id": "return", "label": "Send back to Purchasing"},
            {"id": "approve-silent", "label": "Approve"},
        ],
        "expected_action": "return",
        "cues": ["2.5", "€50", "50", "tolerance", "purchasing", "exceed", "above"],
    },
]

TRIAL_RUBRIC_PUBLIC = {
    "s-capex-classification": "Classifies equipment spend according to the company's capitalisation practice, and "
    "explains the deciding factor.",
    "s-duplicate-detection": "Identifies whether an invoice has already been paid, using the documents provided.",
    "s-bank-change-escalation": "Handles requests that affect where money is sent safely and to the right person.",
    "s-variance-judgment": "Decides whether a difference between invoice and order is acceptable, and documents why.",
}
