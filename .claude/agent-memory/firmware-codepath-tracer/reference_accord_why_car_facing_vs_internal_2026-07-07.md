---
name: accord-why-car-facing-vs-internal
description: 2020 Accord TVA-A160 V850E2 — synthesis of the 4-tracer swarm + openpilot/opendbc capture check answering "why are 399/427/0x14A car-facing but 0x660/0x19F/0x32E/0x64D internal (invisible on every comma bus)?" ANSWER: not firmware-grounded yet — every STATIC routing mechanism is ruled out; the decision lives in unlocated dynamic-RAM producers (0xFEDF68BC registration table + STATUS[idx] pending table) or in physical-layer config outside code.bin.
metadata:
  type: reference
---

# Why are some EPS CAN frames car-facing and others internal? (2026-07-07 swarm synthesis)

Platform: 2020 Honda Accord 39990-TVA-A160, Renesas uPD70F3508/V850E2. Stock `code.bin`.
Question: 399/0x18F, 427/0x1AB, 0x14A are seen by the comma (bus 1); 0x660, 0x19F, 0x32E, 0x64D are
absent on every comma bus (live scan 38409 frames/10 s + rlogs). WHY?

## Bottom line

**We do NOT have a firmware-grounded explanation — but the swarm converted an open mystery into a precisely
localized one.** Every *static* routing mechanism a comma-visibility split could hide in has been ruled out by
independent traces. What remains is dynamic runtime state whose producers static analysis could not reach, plus
a physical-layer config that is not in `code.bin` at all.

## What was RULED OUT (each by an independent tracer, cross-reconciled)

| Candidate mechanism | Verdict | Evidence (agent) |
|---|---|---|
| Second CAN controller / second bus (car-facing on FCN0, internal on FCN1) | **RULED OUT** | Only FCN0 (0xFF480000) is clocked, buffer-configured, and globally enabled (`FCN0GMCLCTL.PWOM=1` @0xdf5e). FCN1 (0xFF4A0000) gets zero init; the only 3 raw `0xFF4A8000` byte-matches are flash padding, not code. (Segment 3 / init) |
| A static per-message "channel" / bus / mailbox field | **RULED OUT** | Table-B channel byte 0xB7208 == 6 for all 17 entries; mailbox assignment is a **runtime dynamic pool** (RAM table 0xFEDF68BC+idx*2), not a static per-ID field. "There isn't one to find." (Segment 2 / mailbox map, + D) |
| Transmit-request (CSETR) gating by CAN ID | **RULED OUT** | `FUN_0001d68e` never writes CSETR; every real CSETR write is boot-time and buffer-index-keyed. Buffer 0 = CSETR-clear special case; other buffers incl. 6 = CSETR-set. Not ID-keyed. (Segment 1 / trigger path) |
| Software builder gating / cadence difference | **RULED OUT** | All 7 builders (car-facing + internal) share the identical dispatch chain: scheduler 0x45db0 → FUN_0001e286 → FUN_0001dcaa (polls FCN0M{idx}CTL TRQF/TCPF) → FUN_0001d96e/db74 → FUN_0001d68e. Every gate keys on mailbox index / HW state, never message identity. (Segment 4 / lifecycle) |
| Internal IDs consumed by an on-board peer (RX/loopback) | **RULED OUT** | Whole-image search: none of 0x660/0x19F/0x32E/0x64D appear in any RX-shaped MID0H/MID1H match table. They are pure outbound. (Segment 4) |

Net: a single controller running an **ID-blind, dynamically-pooled** TX path would — taken literally — put all
seven frames on the one bus the comma taps. Only three appear. So the discriminator is NOT in any of the traced
static code.

## Where the answer MUST live (localized, not yet read)

1. **The producers of two dynamic RAM tables** — both unlocated by all four agents because they are compile-time
   `gp`+small-displacement stores that absolute-literal scans cannot see, and because r2's `v850.gnu` mis-decodes
   key instructions in these driver regions:
   - **`0xFEDF68BC` mailbox-registration table** (which logical message is "registered" to which pooled mailbox).
   - **`STATUS[idx]` pending table** (`gp-0x1744`, which mailbox is marked ready-to-service).
   If the producer only **registers / marks pending the 3 car-facing IDs in normal driving** (and enqueues the
   4 internal IDs only under a diagnostic / bench / special mode), that is the whole explanation — and it is
   fully consistent with everything above. **This is the leading hypothesis.**
2. **Physical-layer routing outside `code.bin`.** Segment 3 found **no pin-mux (PIPC) writes anywhere in
   `code.bin`** despite FCN0 demonstrably working → the CAN pin config (and any second transceiver, or a gateway
   ECU that forwards only the car-facing subset onto the comma-tapped bus) is set up by the **bootloader** or by
   **another ECU**, neither of which is in this binary. Cannot be confirmed or refuted from `code.bin` alone.

## Corroborating capture-side evidence (openpilot / opendbc, cloned to ../openpilot)

- Our `tools/comma4_can_inventory.py` is **raw** — it records every `(bus, addr)` from `p.can_recv()` with
  **no DBC filtering**. openDBC cannot be the reason the internal IDs are missing from our scan. (Rules out the
  "our tool filtered them" hypothesis.)
- The 2020 Accord (Honda Bosch platform) uses the `honda_civic_hatchback_ex_2017_can` DBC set. It documents the
  three car-facing EPS transmits — 330=STEERING_SENSORS, 399=STEER_STATUS, 427=STEER_MOTOR_TORQUE — and
  **defines none of 0x19F/0x32E/0x64D/0x660** (not even as comments). Years of comma raw-logging never captured
  them on the harnessed bus → **circumstantial corroboration** that they don't reach it. Not proof.

## Two ways to actually CLOSE it

1. **Ghidra dataflow** on the driver cluster (with the SVD loaded). `v850.gnu` is demonstrably insufficient here
   (Segment 2 had to pull GNU binutils `v850-opc.c` to decode `ld.bu D16_16[ep],rX`; Segments 1 & 3 hit an
   undecodable `a2 07` opcode). Ghidra's xref/dataflow can find the `0xFEDF68BC` and `STATUS[idx]` **writers** —
   the one thing four static r2 passes could not. Highest-value next static step.
2. **Live trace on the car** (definitive): dump the `0xFEDF68BC` / `STATUS[]` RAM while the ECU runs, or scope
   the physical EPS CAN pins, to see whether 0x660 et al. are ever registered/on-wire in normal driving vs only
   under a diagnostic condition.

## ⚠ Practical consequence for the telemetry-frame build (IMPORTANT)

**0x660 is living proof that being in Table B does NOT guarantee comma-visibility.** 0x660 is a fully-populated
Table-B TX entry with a builder, yet it never reaches the comma. Therefore the earlier plan "add the telemetry
frame by extending Table B" is **necessary but NOT sufficient** — a naively-added frame could behave like 0x660
(invisible) instead of like 399 (visible). Before building V36 telemetry we must identify what makes 399 get
registered/enqueued for the car-facing path and 0x660 not — i.e. the same unlocated dynamic-producer above. This
revises the confidence of the prior `reference_accord_can_tx_synthesis_2026-07-07.md` "new frame → same wire as
399" conclusion: true at the FCN0/physical level, but gated by a registration mechanism we have not yet decoded.

## Cross-references
- `reference_accord_can_tx_trigger_path.md` (Seg 1), `reference_accord_can_tx_mailbox_index_map.md` (Seg 2),
  `reference_accord_can_init_mid_pinmux_topology.md` (Seg 3), `reference_accord_internal_id_lifecycle.md` (Seg 4).
- `reference_accord_can_tx_synthesis_2026-07-07.md` + `_fcn0_forward_verify.md` (prior swarm this builds on).
