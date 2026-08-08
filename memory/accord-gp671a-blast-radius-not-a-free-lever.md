---
name: accord-gp671a-blast-radius-not-a-free-lever
description: "gp-0x671a has FOUR external consumers besides the r24/r26 rate lanes, so lowering the detector threshold T changes five things at once — it is not a clean GATE 1."
metadata: 
  node_type: memory
  type: reference
  originSessionId: bc782257-b6f6-4f50-b561-9f5907a74209
  modified: 2026-07-31T22:46:21.005Z
---

The oscillation detector's output `gp-0x671a` is **not private to the r24/r26 rate-lane gain arms.**
Byte-scanned both gp-relative encodings, whole image, 2026-07-31: **8 real hits, 6 reader functions**
(sole writer `0x42A12`). Four readers are external to both the detector and the aggregator:

- **`FUN_0003a382`** — uses it as a **CONTINUOUS LERP index**, not a binary gate, shaping the live
  P/I/D residual lane `gp-0x6ad4`. This is the worrying one: it makes `T` a *shape parameter* on a lane
  already known to be load-bearing (V56 muted its ceiling `0xC6AF0` and it cost damping).
- **`FUN_00036c12`** — friction-comp lane `gp-0x6b26`, which sums into **the same aggregator**.
  ⚠ Its own gate uses cal `0xC64FD`, **not** CEIL — so lowering CEIL doesn't retune it, but lowering T does.
- **`FUN_000352b4`** — gates a 2nd-order IIR update.
- **`FUN_00035b20`** — selects between two LERP-blend curves.

⇒ **Lowering `T` (`0xC620A`) changes FIVE things simultaneously**, four of them uncontrolled. That is why
V62's unconditional `sar` edit was preferred over a T reduction, despite T being viable on sizing grounds
(see [[accord-gp6c2c-is-motor-rate-derivative]]).

**Contrast, byte-verified the same way:** `gp-0x67df` (FSM state) is **clean — 2 hits, both inside
`FUN_000428d4`**, no external readers. And `T` itself has **4 readers, all inside the detector** — the cal
is private even though its *effect* is not. `CEIL` (`0xC64FA`) is **not** private: 3 external readers
(`FUN_000352b4`, `FUN_00035b20`, `FUN_0003aa2c`).

🛑 **`0xC64FA` is a BYTE cal = 5, read by `ld.bu` @`0x3AA78`.** A halfword read gives 517 and is wrong.

✅ **`gp-0x671a` does not appear to gate a fault.** It is logged into a diagnostic record array on every
low-torque tick (`FUN_00045608(2, …)`), but the DTC-0x21 dispatch in that tail reads a *different* array
(`gp-0x6544[2]`, producer untraced). Stated as "touches diagnostic logging, does not gate a fault" —
not chased to full closure.
