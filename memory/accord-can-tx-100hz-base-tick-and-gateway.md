---
name: accord-can-tx-100hz-base-tick-and-gateway
description: "Accord EPS CAN-TX base tick is 100 Hz, not the 62.5 Hz on record; and the gateway per-ID whitelist is now confirmed on 8 controls — so FOURFRAME's absence from comma rlogs proves nothing about whether the cave fired."
metadata: 
  node_type: memory
  type: reference
  originSessionId: e83f5d10-c983-4d72-862d-9c17c6f2e166
  modified: 2026-07-26T21:57:41.870Z
---

Both facts read with **pure Python** (dispatch tables in the plain image + rlog frame counts) — no
disassembler needed.

**Base tick = 100 Hz, NOT 62.5 Hz.** Derived three ways from `cadence x measured wire rate`, all
agreeing: slot 7 `0x1AB` cadence 2 @ 50 Hz; slot 9 `0x18F` cadence 1 @ 100 Hz; slot 10 `0x14A`
cadence 1 @ 100 Hz. CAN 399 independently fitted at **exactly 100.000 Hz** (period 10.0000 ms).
⇒ any packer-hooked telemetry samples at 100 Hz (Nyquist 50 Hz).

**Gateway whitelist, now 8 controls instead of 1.** Of the 11 EPS broadcast slots, only `0x14A`,
`0x18F`, `0x1AB` reach the comma; `0x720-0x723`, `0x660`, `0x64D`, `0x32E`, `0x19F` never do — and
slot 8 (`0x19F`) is configured **identically** to slot 9 (`0x18F`): same mailbox 6, same cadence,
same payload mechanism. ⇒ **a new CAN ID's absence from a comma rlog is expected and carries NO
information about whether the firmware cave fired.**

**How to apply:** don't plan a red-panda confirmation without first checking the tap point —
`docs/RED-PANDA-EPS-SETUP.md` routes the red panda through the *same* comma Bosch harness, so it
would see the same filtered set. For comma-visible telemetry prefer free bytes in gateway-crossing
frames: **`0x18F` byte5 (constant 0x00) + `0x14A` byte4 (constant 0x07)** give a full 16-bit signal at
100 Hz via the spare-bit piggyback class that has flashed successfully four times. `0x1AB` is a poor
carrier (DLC only 3; bytes 0-1 are a live saturated signal, not the "unused near-zero" frame on record).

Also: the rlog fingerprint shows `eps fw='39990-TVA,A160'` — the comma proves a modified image is
running but **every build in this kit shares that string**, so an rlog cannot identify which one.

Related: [[accord-vibration-requires-lkas-engaged]].
