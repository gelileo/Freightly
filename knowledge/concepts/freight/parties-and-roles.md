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
| **Shipper / "middle man"** | Justnano INC — handles all broker communication | Hughson Huang, President, `hs@justnanoinc.com` |
| **Broker** | Priority-1, Inc. — intermediary between shipper and carrier | Will Jerry (`William.Jerry@priority1.com`); `ltlwest@priority1.com` (cc) |
| **Carrier** | The trucking company actually moving freight | AAA Cooper Transportation (code SCM) |
| **Receiver / consignee** | Destination for the shipment | (unnamed; can unload / pick up at terminal) |

Justnano never contacts the carrier directly — Priority-1 relays.

## Freight terms

- **BOL** — Bill of Lading number; used here as the **case key**.
- **PRO#** — carrier's progressive/tracking number for the shipment.
- **POD** — Proof of Delivery.
- **LTL** — Less-Than-Truckload (the shipping mode; cf. the `LTL-mail/` corpus).
- **Liftgate / bobtail** — delivery equipment; their limits drive oversized/`damage` access issues.

## Confirmed across the corpus (2026-07-09)

Verified against the 71-file `LTL-mail/` corpus and generated `cases/<BOL>/thread.md`:

- The broker side is almost always the **shared mailbox `ltlwest@priority1.com` (LTL West)**,
  sent via the **Front** shared-inbox tool (`[Sent from Front]`), and signed by rotating
  individual **LTL Support Analysts – West** — observed: Isabella Guerrero, Laura Posada,
  Lauren Moore, Shyra Shannel Dela Cruz, plus named reps like Jalen Turner. When drafting,
  address the human name from the latest reply's signature; fall back to "team".
- The shipper side is consistently **Hughson Huang / Justnano INC** (`hs@justnanoinc.com`;
  booking login `huang@justnanoinc.com`).
- **One carrier named so far:** AAA Cooper (code SCM); other carriers (e.g. ABF, seen as
  "Relayed to ABF") appear only as broker mentions, never as direct correspondents — the
  shipper→broker→carrier chain holds throughout.
