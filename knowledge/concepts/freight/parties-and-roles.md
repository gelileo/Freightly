---
title: Parties and Roles
type: concept
area: freight
updated: 2026-07-09
status: mature
---

# Parties and Roles

The communication chain and the freight terms used throughout the corpus.

## The chain

```
Customer ──WeChat (Chinese)──▶ Shipper (Justnano) ──email (English)──▶ Broker (Priority-1) ──▶ Carrier
```

| Party | Role | In the sample thread |
| --- | --- | --- |
| **Customer** | End client who raises the issue; not on the email thread | (via WeChat; not shown in `.eml`) |
| **Shipper / "middle man"** | the shipper (agent) — handles all broker communication | shipper operator (President), configured mailbox |
| **Broker** | Priority-1, Inc. — intermediary between shipper and carrier | Will Jerry (`William.Jerry@priority1.com`); `ltlwest@priority1.com` (cc) |
| **Broker (sales)** | Priority-1 Account Executives who prospect for new/repeat business — never move an actual shipment; their mail is `triage == skip` (promo) | Ashton Johnson, Account Executive – Digital (`Ashton.Johnson@priority1.com`); real example: `LTL-mail-2/10% Off Freight Promo LTL, Truckload And Expedited.eml` ("we have a promotion … 10% discount for all new shippers") |
| **Broker (statements, automated)** | Priority-1's automated billing mailbox — sends monthly statements / invoice notifications, never a human reply; its mail is `triage == skip` | `NoReply@Priority1.com` (From header: "Priority1 Statement") |
| **Carrier** | The trucking company actually moving freight | AAA Cooper Transportation (code SCM); ABF (mentioned only, "Relayed to ABF"); **Warp** — seen relaying an out-of-route charge ("Please see below from Warp on the out of route charge … $55.56 out-of-route mileage fee", `LTL-mail-2/BOL 60114409180 _ P-118701-2621.eml`) and, in a separate thread, a TONU fee ("Warp advised below on yesterdays PU … a TONU (Truck Order Not Used) fee of $100 will apply", `LTL-mail-2/BOL 60114716390.eml`) |
| **Receiver / consignee** | Destination for the shipment | (unnamed; can unload / pick up at terminal) |

Justnano never contacts the carrier directly — Priority-1 relays.

## Freight terms

- **BOL** — Bill of Lading number; used here as the **case key**.
- **PRO#** — carrier's progressive/tracking number for the shipment.
- **POD** — Proof of Delivery.
- **LTL** — Less-Than-Truckload (the shipping mode; cf. the `LTL-mail/` corpus).
- **Liftgate / bobtail** — delivery equipment; their limits drive oversized/`damage` access issues.
- **FFBA (Free Freight Bill Audit)** — Priority1's own post-shipment audit of the carrier's
  final freight bill against the original quote; when it finds a discrepancy it can add a
  **pricing variance** (extra charge) to the invoice, subject to dispute within a stated window.
  Real quote: "processed through Priority1's Free Freight Bill Audit and have accrued a
  pricing variance … Priority1 CAN dispute these charges on your behalf within 2 BUSINESS
  DAYS" (`LTL-mail-2/FFBA BOL# 60112079078.eml`). Drives the `billing-dispute` issue type
  (see `templates/billing-dispute.md`, `connections/issue-to-template-flow.md`).
- **Out-of-route charge** — extra mileage fee when the driver is redirected to a different
  pickup/delivery address than originally tendered. Real quote: "since the driver has to
  route to a new location, this address change will incur an additional $55.56 out-of-route
  mileage fee" (`LTL-mail-2/BOL 60114409180 _ P-118701-2621.eml`, carrier Warp via broker
  Will Jerry). One of the `billing-dispute` triggers in `scripts/triage.py`'s `_BILLING`.
- **Accessorial (charge)** — any extra service fee beyond base linehaul (e.g. liftgate,
  residential delivery, inside delivery, limited access); billed on top of the quote and
  subject to the same FFBA dispute path as a pricing variance.
  Another `_BILLING` trigger term.
  See the multi-BOL variance notice `LTL-mail-2/Variances for BOL 60114661539,
  60114679634, & 60114539432.eml` (e.g. "Residential Delivery" as a variance reason).
- **Reweigh / reclass** — FFBA finds the carrier physically reweighed the freight and/or
  changed its NMFC freight class, changing the billable weight/class and therefore the price.
  Real quote: "Reweighed from 552 lbs to 1138 lbs. Reclassed from 125/250 down to 100/125"
  (`LTL-mail-2/FFBA BOL# 60112079078.eml`); another instance: "Reclass from 55 to 60 …
  Density found to be 32.8" (`LTL-mail-2/Priority1 Variance Update for Shipment
  60111754054.eml`). Both are common `billing-dispute` reasons.
- **PO# (purchase order number)** — the receiver's own internal order number; some
  appointment-required receivers won't schedule a delivery without it. Real quote: "I am in
  need please of a PO# in order to schedule this delivery it is an appt stop and they are
  requesting PO#" (`LTL-mail-2/60112049235.eml`); a `[[MISSING: PO#]]` slot when the customer
  hasn't supplied one and the receiver needs one to schedule.
- **Drayage** — short-haul trucking of an ocean/rail container between a port/rail terminal
  and a local facility (as opposed to long-haul LTL/FTL linehaul). **Out of this project's
  v2 scope** — real quote: "Drayage moves --- 40HQ from Phoenix Terminal to Tempe, AZ …
  Please advise: Drayage cost / Free time at terminal / Any additional charges"
  (`LTL-mail-2/RE_ Drayage moves --- 40HQ from Phoenix Terminal to Tempe, AZ.eml` and its
  ~23 snapshots). Even though its body literally contains "additional charge(s)" (which
  would otherwise trip the `billing-dispute` `_BILLING` regex), `scripts/triage.py`
  special-cases the "Drayage cost / Free time at terminal" idiom to `skip` — it is a quote
  request for an out-of-scope service, not a real billing dispute.

## Confirmed across the corpus (2026-07-09)

Verified against the 71-file `LTL-mail/` corpus and generated `cases/<BOL>/thread.md`:

- The broker side is almost always the **shared mailbox `ltlwest@priority1.com` (LTL West)**,
  sent via the **Front** shared-inbox tool (`[Sent from Front]`), and signed by rotating
  individual **LTL Support Analysts – West** — observed: Isabella Guerrero, Laura Posada,
  Lauren Moore, Shyra Shannel Dela Cruz, plus named reps like Jalen Turner. When drafting,
  address the human name from the latest reply's signature; fall back to "team".
- The shipper side is consistently the shipper operator / shipper company (configured mailbox;
  booking login `huang@example.com`).
- **One carrier named so far:** AAA Cooper (code SCM); other carriers (e.g. ABF, seen as
  "Relayed to ABF") appear only as broker mentions, never as direct correspondents — the
  shipper→broker→carrier chain holds throughout.

## v2 additions (`LTL-mail-2/`, 2026-07-09)

The scope-widening corpus (`LTL-mail-2/`, 851 files, Justnano's full broker inbox — see
`platform-architecture.md`'s "decision | v2 scope" entry) surfaces parties and terms the
71-file `LTL-mail/` sample never showed:

- **Warp** — a second named carrier (alongside AAA Cooper and ABF-by-mention), seen taking
  direct instructions from and reporting back to broker Will Jerry (out-of-route charge,
  TONU fee) — the shipper→broker→carrier chain still holds, Justnano never contacts Warp
  directly.
- **Ashton Johnson** (`Ashton.Johnson@priority1.com`) — a Priority1 Account Executive
  (sales), distinct from the `ltlwest@priority1.com` support-analyst rotation; his mail is
  outbound prospecting, always `triage == skip`.
- **`NoReply@Priority1.com`** — the automated sender for monthly statements/invoices;
  `scripts/triage.py`'s `_SKIP_SENDER` matches on this address specifically (case-
  insensitively) to route statement mail straight to `skip` without reading the body.
