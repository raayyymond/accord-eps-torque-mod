---
name: accord-dtc-read-is-structurally-blind-here
description: 0xF00049 is a catch-all shared by ~42 fault_ids and its UDS status is NOT an OR across members — the display picks a winner from a RAM fault log the power cycle clears, falling back to fid 4. A fresh 0x1c/0x1d trip is invisible in a 19 02 read taken after a restart. Also — 0x23 ReadMemoryByAddress is not implemented on this ECU.
metadata:
  type: reference
---

# 🛑🛑 THE DTC READ IS STRUCTURALLY BLIND HERE — do not treat it as the decisive measurement

The V75 refutation ledger closed with *"the decisive outstanding measurement is a DTC read."* **It is
not, and here is why.**

## 1. `0xF00049` is a CATCH-ALL shared by ~42 distinct fault_ids
Its status byte **cannot identify which monitor fired, even in principle.** Every `0x3D01`-class monitor
and a long tail of unrelated ids funnel into the same displayed DTC.

## 2. A multi-member group's UDS status is **NOT an OR across its members**
The display picks a **winner** from a **live RAM fault-log array** (pointer `tp-0x7fcc`) **by priority**,
and falls back to the **group's first ROM member** — which is **fid 4, a power-on self-test** — when the
log has nothing. 🛑 **The RAM log is cleared by the power cycle.**

⇒ **a fresh `0x1c` / `0x1d` trip is INVISIBLE in a `19 02` read taken after a restart.** The read
returns fid 4's stale framing and reads like a boot self-test, which is exactly the wrong story.

## ★ Provenance [EVIDENCE, orchestrator-verified from the raw ISO-TP capture]

`flashing-2020accord/dtc_script_output_stock_eps_preV21new.txt` — taken on **stock firmware, before this
kit's first flash** — shows:

```
5902ce  540011 40  c41668 08  d48394 40  f00049 48  f00055 40
```

Today's read differs from that in **exactly two bits**: `0xC41668` gained `pendingDTC`, `0xD48394` gained
`confirmedDTC`. **`0xF00049` is byte-identical to stock.**

✅ The store IS responsive — `dtc_script_output_2.txt` shows `f00049 = 0x0E` when it genuinely fires. So
the null is a property of *when* the read is taken and *what the group encodes*, not a dead register.

## 🛑 `0x23` ReadMemoryByAddress is NOT implemented on this ECU
NRC `0x11` in **all three captures, across three firmware eras.** Do not plan a diagnostic around it —
telemetry has to ride the probe cave or a repurposed DID
([[reference_accord_uds_did_read_surface_a160]]).

## How to apply
- Never quote a post-restart `19 02` as evidence that a monitor did **not** trip.
- If a DTC read is wanted, it must happen **before** the power cycle, and even then it can only say
  *"something in the `0xF00049` group"*.
- The discriminating instrument here is a **probe cave bit on the descriptor word**, not UDS — see
  [[accord-descriptor-bit13-is-the-fault-fingerprint]] for the bit that actually partitions the ids.
- 🛑 Any live CAN/UDS send still needs explicit operator confirmation of the exact payload.

Related: [[accord-v75-fault-pinned-to-the-frame]] · [[reference-accord-v75-fault-refutation-ledger]] ·
[[feedback-probe-the-gate-not-just-the-output]]
