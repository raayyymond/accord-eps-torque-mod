---
name: accord-r24-gain-is-a-speed-rate-surface
description: r24's gain is a two-axis speed×rate LERP surface; the units were got wrong once and are now settled empirically; a flat arm inverts Honda's own schedule
metadata:
  type: reference
---

★★★★ **r24's gain is NOT a scalar.** `FUN_0003ad74` rebuilds it every cycle by cross-interpolating four
ROM records on **VEHICLE SPEED** (`gp-0x6a5e`; cross axis `0xC6010` = `[0, 640, 3200, 6400]` =
0 / 9.99 / 49.95 / 99.9 km/h) and then LERPing on **MOTOR RATE** (`gp-0x6ac0`). Byte-verified in stock
`code.bin` and in `_v65`/`_v66`/`_v67_plain_image.bin`; ladder and arithmetic confirmed in Ghidra three
independent ways (decompile edge cases, stack-slot pairing, and the two clamp branches).

Record layout **20 bytes**: `u16 count=4`, `X[4]`, `Y[4]`, pad. Mode 10 → `0xD2A74`(0 km/h) /
`0xD2AB0`(10) / `0xD2AEC`(50) / `0xD2B28`(100); mode 11 → `0xD2A88`/`0xD2AC4`/`0xD2B00`/`0xD2B3C`.
ROM layout is **[array1: m10,m11,m12][array2: …][array3: …][array0: …]** — triplets of adjacent modes
per array, so reading "4 consecutive records" from `0xD2AEC` gives array3/m10,m11,m12 + array0/m10, NOT
one mode's speed curve. Honda **rolls the gain off with speed**: 3072 at 0 km/h → 2151 at 100 km/h.
⚠ An agent-memory file (`reference_accord_r24_gainb_table_structure_and_priority_gate.md`) carries the
**INVERTED** array↔breakpoint mapping. `studies/sessions/v68/v66_v67_explained.py` and this note have it right; monotonicity
of Y[0] (3072 > 2561 > 2305 > 2151) only holds under the correct mapping.

## 🛑🛑 UNITS — I GOT THIS WRONG ONCE. Settled empirically 2026-08-02.
**The `0x14A` rate field IS deg/s (factor 1)**, and `gp-0x6ac0` = **4.71210813 counts per deg/s**, so the
inner breakpoints `[0, 400, 1400/1500, 3000]` are **`[0, 85, 297, 637]` deg/s**.

Two independent measurements settle it:
1. **Regress `rate_c` on the differentiated ANGLE channel** (`0x14A` b0:1, factor −0.1 ⇒ degrees):
   slope **0.95–1.00**, r ≥ **0.985** on every clean segment ⇒ the bus field is deg/s.
2. **Physical reachability.** Observed |rate| over **407,617 frames** peaks at **521 deg/s**
   (p99.9 = 408). At 4.7121 counts/deg-s the breakpoints are 85 / 297 / 637 deg/s — **fully exercised**.
   Under the erroneous 0.589 counts/deg-s they would be 679 / 2377 / 5093 deg/s and Honda's 2× rolloff
   would **never engage in any real drive**. Decisive.

**What I retracted, and why it matters as a method lesson:** I had claimed (a) "bus counts = 8 × deg/s
exactly", (b) "the rate axis is arithmetically dead — all three symptom populations sit in the flat
`[0,400]` segment", and (c) "V67's build note contains a units error; its arm delivers 1.94× not 2.00×".
**All three were wrong.** The error was **composing two structural relations I had not verified myself**
(`gp-0x6ac0 = |gp-0x6abe|` and `bus = (gp-0x6abe × 48 × 1159) >> 15`) into a scale, instead of
**measuring** the scale against a channel I already had. One of those two premises is wrong; **which one
is still OPEN** and needs a Ghidra trace. ⇒ **V67's build note was CORRECT** (LERP 2622, arm 5244 =
exactly 2.00×).

## ⇒ The rate axis IS usable — the three populations sit at DIFFERENT points

| population | deg/s | gp-0x6ac0 | LERP segment |
|---|---|---|---|
| grind #1 | ~128 | ~603 | `[400, 1400]` — on the rolloff |
| grind #2 creep | ~256 | ~1206 | `[400, 1400]` — further along the same rolloff |
| grind #2 highway | 30–42 | ~141–198 | `[0, 400]` — flat |

⚠ **GATE 2 caution on any rate-axis edit:** `gp-0x6ac0` is a **rectified** filtered motor rate, so it
sweeps at 2× the mode frequency and a steeply rate-dependent gain modulates at 2f — the parametric-pump
failure mode V58/V59/V60 chased. Stock **already** has a rolloff there, so the mechanism is not new and
is evidently tolerable at stock slope; any edit that **steepens** it must state the new slope and argue
the pump margin. (An earlier version of this note called that a structural veto. It is a quantitative
caution.)

⚠ **One precision correction to my own wording:** I wrote *"Y0 == Y1 in every curve of both LERPs"*.
It is true in every curve **except mode-10's 50 km/h record `0xD2AEC`**, which byte-reads Y0 = **2305**,
Y1 = **2304** (`01 09` then `00 09`). A +1 cal-tool rounding artifact — 0.04%, behaviourally nil — but
**an exact `Y0 == Y1` equality test WILL break on it**, and the value was in my own byte dump the whole
time. The `[0, 400]` segment is flat *to within 1 count*, not exactly flat.

## ★★ A FLAT ARM INVERTS HONDA'S SCHEDULE
| operating point | stock LERP | V62/V65 | **V67** | **Design A** |
|---|---|---|---|---|
| grind #1 — 7.2 km/h, 128 deg/s | 2622 | 2.00× | **2.00×** | **2.00×** |
| grind #2 creep — 5 km/h, 256 deg/s | 2409 | 2.00× | **2.18×** | **1.22×** |
| grind #2 highway — 110 km/h, 35 deg/s | 2151 | 2.00× | **2.44×** | **1.00×** |

🛑 A flat arm is **structurally incapable** of fixing two operating points: one degree of freedom, two
constraints. 1.00× at highway needs arm 2151 = **0.80× at grind #1** (worse than stock).

## ★ DESIGN A — the best-characterised alternative, ONE halfword, pure calibration
`0xD2ABC` (= `0xD2AB0` + 12, the 10 km/h record's `Y[1]`) **2561 → 7051**. Nothing else moves.
Exactly 2.00× at grind #1, **1.22×** at the creep grind #2, **1.00×** at 50/100 km/h.
- **Blast radius clean, two methods**: exactly **one** pointer image-wide per record
  (`0xCBF84`/`0xCC06C`/`0xCC154`/`0xCC23C`); whole-image float32 scan finds **no mirror** (the only two
  coincidences, 400.0 and 1500.0, were traced — one belongs to a different mode-indexed float table at
  `0xC7888` monitoring `gp-0x6a62`/`gp-0x6bbe`, the other is code bytes). Both candidate int/float
  lockstep monitors (`FUN_000347b8`→DTC `0x417a`, `FUN_00035154`→DTC `0x1c`) decompiled and ruled out.
- **CRC block #41** `[0xD2000,0xD2FFC)` only; verified by running the 50-block walk.
- **Saturation** at `|dtorque| ≥ 1190` vs a measured max of 839 (**1.42×** margin, vs V67's 1.91×);
  `mul` worst case 1.68% of INT32_MAX. Fold discontinuity **byte-identical to stock** (Y[0] untouched).
- **Never edited in any build** — `0xD2A74`/`0xD2AB0` appear only as V66's widened tripwire.
- 🛑 **Known costs:** it is **not** LKAS-gated (unlike V67 it changes manual feel at low speed), and the
  multiplier **humps to ~2.45× near 9.9–10 km/h** because `0xD2AB0` *is* the 10 km/h breakpoint record.
- ⚠ Design B (both records, `0xD2A74.Y[1]`→8832 and `0xD2AB0.Y[1]`→4813) hits the same 2.00× but with
  only **1.13×** saturation margin. Design C (raising Y[0] too) makes the fold jump 4.7× bigger. Both
  rejected.

⇒ **Not currently recommended** — V67 already has creep grind #2 at zero bursts and grind #1 fixed, and
the highway shows no dose response, so Design A would trade a measured property (manual creep is
byte-stock) for margin on things already at zero. Recorded as ready if that changes.

Arithmetic: `analysis-2020accord/studies/sessions/v68/v68_design_math.py`.
Related: [[accord-v67-flew-both-grinds-fixed]], [[accord-r24-gain-b-four-pointer-arrays]],
[[accord-no-speed-byte-exists-in-this-firmware]].
