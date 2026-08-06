---
name: accord-v74-flew-damper-is-in-force
description: V74 flew route 5d and bit7 = (gp-0x6bd0 != 0) FIRED -- the first positive control on the base-assist damper in this kit's history. 67.44% engaged creep vs 0.29% manual creep; V72's identical probe read 0/87,940.
metadata:
  type: reference
---

# ★★★★★ V74 FLEW: THE DAMPER IS IN FORCE — the kit's first positive control on `gp-0x6bd0`

**Route `0000005d`, 17 segments, 101,118 frames / 1012.9 s, fs 100.772 Hz.** Measured by me on the
pooled route; every number below is a raw count, not a scaled estimate.

## The result — [EVIDENCE]
`bit7 = (*(short *)(gp - 0x6BD0) != 0)` — **the damper's own output**, not a proxy.

| slice | n | bit7 duty |
|---|---|---|
| **all frames** | 101,118 | **23.342 %** (23,603 frames = 234.2 s of live damping) |
| **ENGAGED** (`latActive`) | 56,753 | **39.927 %** |
| manual | 44,365 | 2.126 % |
| **ENGAGED creep ≤ 4 m/s** | 7,860 | **67.443 %** |
| **manual creep ≤ 4 m/s** | 41,046 | **0.292 %** |

⇒ **engaged-creep / manual-creep = 230.7×.** V72's `bit4` probe read the *same cell* (`|gp-0x6bd0| ≥ 64`)
and fired on **0 of 87,940**. [[reference-accord-two-dead-zones-speed-and-rate]] explains why: both dead
zones were shut.

## ★ THE NEGATIVE CONTROL IS PERFECT, and it re-confirms the mode fall lag on a different cell
All **943** manual bit7 frames lie within **5 s of a disengagement**; **0 of 40,398** manual frames beyond
5 s have it set. 85.6 % sit inside V73's measured **2.08 s fall lag**.
⇒ V74's **engaged-column-only** design is confirmed on-car: manual and parking steering are byte-stock,
exactly as [[reference-accord-car-is-tvca4-mode-24-26]] predicted from the disjoint column sets.
⊕ This is an *independent* replication of V73's 1.02 s rise / 2.08 s fall lag, measured on `gp-0x6bd0`
rather than on the mode byte itself.

## ★ THE POSITIVE CONTROL on the disengaged arm
Disengaged frames clearing **both stock (mode-24) breakpoints** — speed ≥ 2240 counts *and* rate ≥ 60
counts: **n = 157, bit7 = 100.000 %.**
🛑 An earlier statement of this cell as *"183 frames, 99.45 %"* used the superseded **10.0** counts/deg-s
rate scale; at the kit's 4.7121 the cell is 157 frames at **100 %** — see
[[reference-accord-rate-scale-4p7121-stands]]. ⚠ And the honest form of the control is
**"modelled mode-24 dose > 0"** (n = 130, 100.000 %), not "clears both breakpoints": because
`dose = (C×E)>>10` **truncates**, clearing both breakpoints is *not* sufficient for a non-zero dose.

## The delivered dose, priced on the route's own distribution
Mirrors `FUN_00034350` exactly; tables byte-read from `_v74_engagedcols_x0_12_addonly_plain_image.bin`.
Mode 26 as flown: `FactorC X=[2240,3840,5120,8960] Y=[429,234,429,908]` ·
`FactorE X=[12,400,2500,4000] Y=[0,539,539,927]`.

| slice | V74 dose>0 | mean | ≥43 cts | STOCK mean |
|---|---|---|---|---|
| **ENGAGED creep < 4 m/s** (78.0 s) | 65.4 % | **50.3** | **37.4 %** | **0.00 — zero on every frame** |
| ENGAGED ≥ 35 km/h (360.6 s) | 22.6 % | 3.2 | 1.9 % | 0.19 (17.1×) |
| ENGAGED all (563.1 s) | 36.3 % | 15.5 | 10.9 % | 0.12 (128×) |

At the ratchet's own measured rate (99 counts) the dose is **exactly 50** — the design target, inside the
~43 [30, 60] window. **0 frames reached the ceiling.**
🛑 **The unit gap is NOT closed:** the ~43 requirement is in **torsion-bar** counts, this delivery in
**aggregator** counts, and nobody has converted between them (the attempted transfer estimate had
coherence 0.072 and was refused). Exposure and direction are settled; magnitude match is not.

## ⚠ The model that produced the dose column is a LOWER BOUND
Predicting bit7 from `(speed, column-rate)` agrees with the measurement on **91.240 %** of frames
(84.7 % engaged, 99.6 % manual). The residual runs **one way** — 5,522 frames where the model says 0 and
the damper fired, vs 3,335 the reverse — because FactorE indexes the firmware's own **motor** rate
`gp-0x6ac0`, while the model substitutes the 0x18F **column** rate. **Every modelled dose is a floor.**

## Build identity — how this log was proved to be V74
Four discriminators in `decode_v74_probe.identify()`: D1 (manual creep) and D1b (near-zero rate) **pass**;
D3 does not fire; **D2 is UNPOWERED and must not be reported as a pass** (the state field takes a second
value on exactly 1 frame, so its "56.3 % agreement with latActive" is just latActive's own duty).
★★ **The decisive test is one the decoder does not run** — a byte read of `[0xC4B34, +68)`:
**V67–V73 all open their cave with `203e1000` = `movea 0x10,r0,r7`, making bit7 a CONSTANT 1**; V74 opens
with `003a` = `mov 0x0,r7`, making it DATA. Route 5d reads **bit7 = 0 on 76.658 % of frames** ⇒
arithmetically impossible for any build V67–V73.
⊕ Second: `bits 6:3` ∈ {4,5}, and under V73's schema the field is `mode & 0xF` ∈ {8,10} ⇒ not V73.

Related: [[accord-v74-flight-underpowered-both-symptoms-active]] ·
[[reference-accord-factore-x1-is-the-free-dose-lever]] · [[feedback-constant-field-is-not-a-void-cave]] ·
[[reference-accord-gp6ac2-is-a-backdrive-detector]] · [[reference-accord-car-is-tvca4-mode-24-26]]
