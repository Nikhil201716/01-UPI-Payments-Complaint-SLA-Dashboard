# Root-Cause Analysis: UPI Payments Complaint & SLA Performance
**Prepared for:** Digital Payments Support Operations Leadership
**Data window:** 1 Aug 2025 – 30 Jul 2026 (12 months, synthetic data) · **Volume analyzed:** 15,713 tickets

---

## Headline Numbers

| KPI | Value |
|---|---|
| Total tickets | 15,713 |
| Overall SLA compliance | **75.7%** (target: 90%+) |
| Average resolution time | 63.1 hrs (median: 40.4 hrs — the mean is pulled up by a long tail of slow cases) |
| Open tickets (unresolved) | 126 |
| Total disputed transaction value | ₹1.91 crore (₹19,139,639) |

At a 75.7% SLA compliance rate, roughly **1 in 4 complaints breaches its promised resolution window.** This report identifies the three specific, data-backed root causes driving the majority of those breaches, plus two supporting operational findings, and closes with concrete recommendations.

---

## Root Cause #1 — The Fraud & Disputes queue is structurally the weakest link

The **Fraud & Disputes** team has the worst SLA breach rate of any team: **40.9%**, against 24.0% for Tier-1 Support and just 6.0% for Technical Escalations. This isn't a one-off — it's consistent across both categories that team owns:

| Category | Breach Rate | Avg Resolution vs. SLA Target |
|---|---|---|
| Wrong Beneficiary Credited (Misdirected Transfer) | **42.1%** | 120.7 hrs vs. 120 hr target |
| Unauthorized Transaction / Fraud Dispute | **40.8%** | 175.8 hrs vs. 168 hr target |

These are the two single highest-breaching categories in the entire dataset — well above the ~24% breach rate seen across every other category. The average resolution time sits *right on top of* the SLA target in both cases, meaning the team isn't wildly off-track: they're marginally, chronically late on a large share of cases, which is the classic signature of a team operating at capacity with no slack for investigation complexity.

The single largest specific root cause tag within this group is **SIM-swap fraud** (149 breached tickets) — cases that require coordinating with telecom providers and banks simultaneously, which realistically cannot be resolved as fast as a standard dispute.

**Recommendation:** Introduce a tiered fraud-triage step. Route high-confidence, low-complexity cases (e.g., a customer disputing a transaction they simply don't recognize, with no fraud markers) through an expedited track, freeing investigator time for genuinely complex cases like SIM-swap and misdirected-transfer investigations — which should get a realistically longer, explicitly-communicated SLA rather than silently breaching the current one.

---

## Root Cause #2 — The failed-transaction reversal process is the single largest source of raw breach volume

While Fraud & Disputes has the *highest rate*, the **Failed Transaction** category group produces the *highest total number* of breached tickets and the **highest disputed value at risk**:

| Category Group | Breached Tickets | Disputed Value at Risk |
|---|---|---|
| **Failed Transaction** | **1,540** | **₹18,83,188** |
| Fraud & Disputes | 778 | ₹8,99,933 |
| Refunds | 606 | ₹7,51,731 |

This group carries the highest ticket volume overall (6,407 tickets, 41% of all complaints), and its SLA windows are tight (24–72 hrs) because these are meant to be fast, largely automated reversals. When automation fails, a human has to intervene manually — and that's exactly what the root-cause data shows. The **top 4 root causes of SLA breaches company-wide** are all tied to this one process:

1. Manual reversal required — 211 breached tickets
2. Payment gateway timeout — 197 breached tickets
3. Bank-side auto-reversal delay — 182 breached tickets
4. NPCI switch downtime — 177 breached tickets

Combined, these four causes alone account for **767 breached tickets** — more than the entire Fraud & Disputes category group.

**Recommendation:** Reduce dependency on manual reversal by tightening the auto-reversal trigger logic (e.g., an automatic retry-and-reverse job for gateway timeouts before a human ticket is even created), and set a clear internal escalation trigger so any transaction still unreversed at T+18 hours is proactively flagged, rather than discovered only after breaching the 24-hour SLA.

---

## Root Cause #3 — Unassigned tickets breach SLA more than any actively staffed team

**235 tickets (1.5% of volume)** never received an agent assignment in the raw data. These "Unassigned" tickets have a **29.8% SLA breach rate** — worse than Tier-1 Support (24.0%) and dramatically worse than Technical Escalations (6.0%). A ticket with no owner has no one actively tracking its clock, so it's structurally more likely to slip past its deadline unnoticed.

**Recommendation:** Add an automated routing safety-net: any ticket unassigned for more than 30 minutes should auto-escalate to a team lead queue, rather than remaining silently unowned until a breach report surfaces it days later.

---

## Two Supporting Findings

**Finding A — Salary-date volume spike is real and predictable.** Complaint volume during the "salary-date window" (25th–2nd of each month) runs at **53.5 tickets/day** vs. **39.3 tickets/day** the rest of the month — a **36% spike**, consistent with higher transaction volume around payday. Staffing should flex accordingly rather than running flat capacity all month.

**Finding B — Incidents cause volume spikes, but are *not* the biggest SLA risk (a genuinely counter-intuitive result).** The three simulated incident days averaged **129.7 tickets/day** — roughly 3x normal volume (42.4/day) — driven almost entirely by Transaction Failed (164 tickets) and App Technical Error (162 tickets). Yet the SLA breach rate *on* incident days was actually **lower** (15.4%) than on normal days (24.5%). The likely explanation: incidents are visible, urgent, and get all-hands attention the moment they're detected, so the resulting tickets get resolved fast even under a volume surge. The chronic categories analyzed in Root Causes #1 and #2 — which don't trigger any visible alarm — are the real, quieter threat to SLA compliance. This is exactly the kind of finding a raw KPI dashboard would miss without this deeper analysis: the loud, visible problem (an outage) is not the one actually hurting the SLA number the most.

---

## Summary Recommendation Priority

| Priority | Action | Root Cause Addressed |
|---|---|---|
| 1 | Tiered fraud-triage to protect investigator bandwidth on complex cases | #1 |
| 2 | Tighten auto-reversal logic + T+18hr proactive escalation flag | #2 |
| 3 | Auto-escalate any ticket unassigned for 30+ minutes | #3 |
| 4 | Flex Tier-1 staffing up ~35% during the salary-date window | Finding A |

*Methodology note: this analysis is built on a synthetically generated dataset modeled on real RBI digital-payment complaint categories and realistic fintech support operational patterns (see [`README.md`](../README.md) for full data-generation methodology). The patterns above were deliberately engineered into the data generator to demonstrate root-cause analysis technique on a working, reproducible pipeline — the same analytical approach applies unchanged to a real ticketing-system export.*
