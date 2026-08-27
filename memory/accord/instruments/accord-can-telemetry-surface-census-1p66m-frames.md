---
name: accord-can-telemetry-surface-census-1p66m-frames
description: A 1.66M-frame census over 30 routes and 29 builds settles the CAN telemetry surface empirically — 0x14A is proven byte-transparent, 0x14A byte7[7:6] is free to the wire, 0x18F byte5[4] is LIVE on two routes, 0x18F has no byte 7, and 0x1AB MOTOR_TORQUE varies.
metadata:
  type: reference
---

★★★★ **THE CAN TELEMETRY SURFACE, SETTLED EMPIRICALLY.** 2026-08-08. Census over
**1,662,374 `0x14A` frames, 30 routes, 29 builds**, **two independent implementations agreeing exactly.**
This sharpens [[accord-can-tx-gateway-whitelist-and-20-free-bits]]; the gateway-whitelist and hook
findings there are unchanged.

## ✅ `0x14A` IS PROVEN BYTE-TRANSPARENT, END TO END [EVIDENCE]

The proof is a **counterfactual**, not an absence: **93.2% of frames carry non-zero magprobe bits in
`byte4[7:3]` — bit positions NO DBC defines.** A gateway that re-serialised from a signal list would
have dropped those bits and emitted a **wrong checksum in 85.5% of them**. It never does, in
**1.66 M frames**. ⇒ the frame reaches openpilot **byte-for-byte as the EPS built it.**

## ✅ `0x14A byte7[7:6]` IS FREE **AND SURVIVES TO THE WIRE** [EVIDENCE, two agents, two methods]

Stock touches the buffer cell `gp-0x1511` at **exactly two read-modify-writes, and both preserve 7:6**:

| site | instruction | relative to the 330 hook |
|---|---|---|
| `0x55BFC` | `andi 0xcf` | **pre**-hook |
| `0x55C24` | `andi 0xf0` | **post**-hook — and it still leaves 7:6 alone |

🛑 **`byte7[5:4]` is NOT free** — it is `gp-0x6880 & 3`, packed at `0x55BF6`/`0x55BFA`.

## 🛑 `0x18F byte5[4]` IS CONFIRMED LIVE ON THE WIRE — the canonical "empirical zero ≠ free" case

**14,472 frames** carry it set — but **only on routes `5e` and `61`, the two hard-fault flights**, exactly
coincident with `STEER_STATUS` → 7. On **28 of the 30 routes it is flat zero.**
⇒ **This is the kit's canonical proof that a bit reading zero across whole drives can still be a live
signal.** `0x1AB byte0[1]` is worse still: **27 frames in 831,200.**

## 🛑 `0x18F` HAS NO BYTE 7 — DLC = 7 in 100% of frames

**`byte6[6]` is the last usable bit.** Any spec that reaches for `0x18F byte7` is writing off the end of
the frame.

## ⚠ `0x18F`'s transparency does NOT transfer from `0x14A` [BELIEF ONLY]

Every bit ever observed in `0x18F` is a stock signal that a re-serialising gateway would also pass, so the
census cannot discriminate. **What would settle it:** one build writing a **known non-stock pattern into
`0x18F byte4[2:0]`** while keeping a **live `0x14A` write in the same flash as an in-flight positive
control.** Until then, treat `0x18F` spare bits as unproven end-to-end.

## 🛑 `0x1AB` `MOTOR_TORQUE` VARIES ⇒ FORBIDDEN AS A CHANNEL

The recollection that *"a steering torque value reads 0"* is about **openpilot's decoded
`steeringTorqueEps` being SMALL** (the V81 handoff uses it as a ring detector at magnitudes < 15), **not**
about the underlying bits being unwritten. Those bits move. Do not overwrite them.

## The ledger

**Clean tier = 16 bits** — 5 in use (`0x14A` b4[7:3]) + `0x14A` b7[7:6] (2) + `0x18F` (6) + `0x1AB` (3).
**This matches the existing memory's count exactly**, arrived at by a completely different method.

Related: [[accord-can-tx-gateway-whitelist-and-20-free-bits]] ·
[[reference-accord-piggyback-channel-audit-dbc-panda]] · [[accord-0x18f-payload-one-frame-stale]] ·
[[feedback-probe-the-gate-not-just-the-output]] · [[feedback-telemetry-must-reserve-a-did-not-fire-value]]
