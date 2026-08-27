---
name: accord-feedforward-lane-exists-one-cal-byte
description: "Honda already built a post-governor feedforward lane and four assist channels already use it. LKAS is slot 1 and is on the governed lane. Moving it is ONE calibration byte: 0xC4124[1] from 0 to 5. Both cal tables have ZERO writers and the ASIL monitor dispatches on the same byte so it follows by construction. It is a TOPOLOGY change, not an authority change - it does NOT buy back steering rate."
metadata:
  type: reference
---

# 🛑🛑★★★★★ THE FEEDFORWARD LANE ALREADY EXISTS — AND LKAS IS ONE BYTE FROM IT

2026-08-23, answering the operator's *"add a separate feedforward path… for more LKAS-driven demand
going to the EPS motor torque aggregate while continuing to mute or filter the steering wheel
feedback."*

## THE ROUTER
`FUN_00026c80` (task 1, 1 kHz, dispatcher slot `0x15`) routes each of 11 assist channels on the cal
byte `0xC4124[i]` (`tp+0x5124`). Bytes, stock and every build: **`[0,0,5,0,5,5,0,0,0,5,0]`**.
```
                  slot request  gp-0x62f8[i]
                ROUTER  0xC4124[i]
     mode 0 ──────────┴────────── mode 5
        |                            |
  gp-0x62b0[i]                  gp-0x62c8[i]
  Σ → gp-0x6b4c                Σ → gp-0x6b4e → gp-0x6afe
        |                            |
  🔴 AGGREGATOR FUN_0003aa2c  (11 unweighted adds: LKAS + EVERY damping term)
  🔴 GOVERNOR   FUN_0004503c  (authority xB, slew ±512/±205)
  🔴 comp-add FUN_000456a4, 🔴 shaper FUN_00042af8
        └──────────────┬─────────────┘
                sum @ 0x43af4 → clamp ±gp-0x4f64 → ±0x2000 → gp-0x6b98 → FOC
```
🛑 **CORRECTS `accord-gp6b4c-is-an-11-slot-assist-sum`**, which says modes (1,2,5,7) → 0 ⇒ slots
{2,4,5,9} FORCED ZERO. **Half right: modes 1 and 2 really do zero; modes 5 and 7 RE-ROUTE.**
**Slots {2,4,5,9} are not dead — they are already on the feedforward lane.**

**Verified by decompile:** mode 5 differs from mode 0 in **exactly four writes** — `gp-0x62b0[i]`
and `gp-0x4b40[i]` → 0, `gp-0x62c8[i]` and `gp-0x4b58[i]` ← request — with `gp-0x6298`, `gp-0x4b28`,
`gp-0x6170`, `gp-0x617c`, `gp-0x625c`, `gp-0x6324`, `gp-0x61e8`, `gp-0x4af8`, `gp-0x61d0` written
**identically** in both. **LKAS is slot 1**: `FUN_0002b422` reads `gp-0x6b3c`, sets `local_1c = 1`,
calls `FUN_00025c32`.

## GATES — all cleared except one bounded item
- **GATE 1.** `0xC4124`: 5 readers, **0 writers**. `0xC4118` (a SECOND 11-byte table, all 1s, which
  gates the GOVERNED sum only — the feedforward sum is **ungated**): 10 readers, **0 writers**.
  Both by Ghidra AND an independent Python LE scan, **set-difference empty**. **No new RAM**; the
  four touched cells are written by `FUN_00026c80` itself, both halves of both shadow pairs, in the
  same basic block ⇒ the `gp-0x1500`-class runtime-index risk does not apply.
- ⭐ **The second reader of each table is the ASIL float plausibility monitor `FUN_00027b0a`, which
  dispatches on the SAME byte** ⇒ it follows the re-route **by construction. No monitor divergence
  is possible.** The single most important safety property of this lever.
- **The authority gate is UPSTREAM.** `FUN_00025c32` @`0x25c32`–`0x25c7c`, before the first payload
  read, compares `gp-0x69aa` against `0xC40F4[slot]` (= 29491 for LKAS) and below threshold zeroes
  `gp-0x62f8[i]` — **the cell the router reads for BOTH lanes.** The cutoff is inherited, not
  bypassed. ⚠ It is an inhibit flag **with hysteresis**, not a hard drop, and what it does depends
  on the request-type byte — identically for both lanes.
- **The `×B` cost is BOUNDED.** `FUN_00049a78` = `min(a,b)`, authority chains are min-cascades
  seeded at `0x8000` ⇒ uninhibited requires `A·B ≥ 29491/32768 = 0.8999` ⇒ `B ≥ 0.8999`.
  **The direct lane can be at most +11.1 % hotter, in a narrow band.**
- **Downstream neutral:** `FUN_00038148` reads BOTH lanes, weights `0xC63AA` and `0xC63A8` **both
  1024 = unity** ⇒ exactly neutral for `gp-0x6ad6`.

## 🛑 WHAT IT DOES *NOT* BUY — the strong form was RETRACTED
*"Every count of damping is a count of LKAS authority"* is **wrong twice**: (a) it holds only AT the
±0x2800 clamp, and V105's `b6` read **0.000000/65,959 frames**, so `|gp-0x6b94|` never reached even
the lower `gp-0x4f64` ceiling; (b) worse, the subtraction is a property of the **final add
`cmd = ff + agg` @`0x43af4`**, downstream of BOTH lanes — **it survives the lane move unchanged.**
⇒ **Moving LKAS does NOT stop the damper opposing it and does NOT buy back steering rate.**
**No extra authority either** — the lane max stays `(0xC61BE × gain)>>15` = **2505 counts at 6×**.

## WHAT IT DOES BUY
① **LKAS leaves the shaper's integrator/blend chain** — a Q15 blend scaled by
`|gp-0x3570>>15| × cal(0xC61DA=1092) >> 10`, i.e. a **state-dependent modulation of LKAS by an
integrator's magnitude** — and becomes **algebraically flat from `gp-0x62f8[1]` to the final clamp**:
no IIR, no integrator, no blend, no slew. That is the closest thing to *"unfiltered LKAS demand
driving the EPS target torque"* the architecture admits.
② Decouples LKAS from the shared slew budget (a coupling, never a cap — LKAS's own max increment is
~78 ct/tick against a 205 ct/tick limit).
⊕ **[BELIEF, untested]** A state-dependent gain in the loop is exactly what produces an
amplitude-dependent crossover. If that blend IS it, moving LKAS off it is a **grinding** lever, not
just a rate one. `gp-0x3570` is not telemetered; nothing in the corpus can test it.

## THE OTHER RANKED OPTIONS
**Rank 2** flatten `0xC520C`/`0xC5224` bank A — Y = [5325,3584,2406,1587,512], a **10.4× collapse
with motor rate**; cal-only, **precedent V41 CHANGE 2 booted and drove clean**; keep both mirrors
identical (the fault-0x17 monitor trips on them disagreeing *between cycles*, not on the value);
SHARED, so it raises the ceiling for the damping terms too. **Rank 3** `0xC61BE` = 15360, unproven.
**Rank 4** a cave at `0x43ae0` — strictly dominated by Rank 1. **Rank 5** `0xC64C8` = 1 — not
recommended.
🛑 **Shadow-lockstep pairs: `FUN_00028d22` protects EIGHT per-slot arrays × 11 slots, plus
`gp-0x4f64`/`gp-0x448a`. "At least six pairs" is badly stale.**

Related: [[accord-gp6b4c-is-an-11-slot-assist-sum]] · [[accord-aggregator-reaches-motor-via-gp6acc-bridge]] ·
[[accord-task1-cave-precedent-and-telemetry-ceiling]] · [[accord-4x-lkas-gain-is-the-frozen-variable]]
