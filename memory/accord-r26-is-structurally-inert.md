---
name: accord-r26-is-structurally-inert
description: "🛑 SPLIT 2026-08-04 into two legs. LEG 1 (the GATE) is REVERSED [EVIDENCE] — it does not kill r26 in ordinary driving. LEG 2 (the MAGNITUDE) is DOWNGRADED to BELIEF — 0xC6564's link to gp-0x69a4 was never verified. 'r24 carries the entire lane' now rests on LEG 2 alone."
metadata:
  type: reference
---

# 🛑 THE "r26 IS INERT" CLAIM HAS TWO LEGS. ONE IS REVERSED, ONE IS DOWNGRADED.

**Filename kept so existing `[[accord-r26-is-structurally-inert]]` links resolve.**
🛑 **This is NOT a flat reversal of the whole claim** — writing it that way would be the mirror image of
the original error. The claim rested on two **independent** legs and they resolved differently.

## LEG 1 — THE GATE: **REVERSED. [EVIDENCE]**
`r26 == 0` **iff** `gp-0x6b5e != 0`, and `gp-0x6b5e = ((LERP(gp-0x6bda) × 0xC63C2) >> 10) × polarity`
(producer `FUN_000361c8` @`0x36256`/`0x36264`, shadow pair `gp-0x4cd8`; `0xC63C2` = 1024 = Q10 unity).
The trapezoid @`0xC66CC` is X = [−384, −128, 128, 294, 384], Y = [0, 4762, 4762, 717, 0] ⇒ r26 is killed
**only where the LERP is ZERO, i.e. `|gp-0x6bda| ≥ 384`.**
★ **And `gp-0x6bda` is a MARGIN TO A PEAK-HOLD ENVELOPE of driver assist torque `gp-0x6bf0`**
(`FUN_00036022` @`0x36068`–`0x3608C`; envelope `gp-0x6bd8`/`gp-0x6bd6` from `FUN_00035d38`, half-width
**never below 9390**; `0xC614A` = ±10048, margin cal `0xC614C` = 128). **Hands-off the margin is ≈ 9262
= 24× the threshold.**

⇒ **THE GATE DOES NOT KILL r26 IN ORDINARY DRIVING, and least of all hands-off at creep.** The kill
window is a **~512-count sliver at the DRIVER-OVERRIDE end** (cf. `0xC6156` = 9216).
**This half is settled, and it is a genuine reversal of how the gate was read.**

## LEG 2 — THE MAGNITUDE: **STILL BELIEF, unresolved in either direction.**
`FUN_00039702` shows the RAM array `gp-0x641E`…`gp-0x6444` is an **adjustment added in Q10 float to a
fixed cal base at `tp+0x7564`**, and **`0xC6564`–`0xC658C` really is 40 bytes of EXACT ZERO** with **no
writer found for the RAM side (10 of 18 cells checked)**. So `stage1 ≈ 0` — **IF that cal base is what
actually feeds `gp-0x69a4`.**

🛑 **THAT LINK WAS NEVER VERIFIED.** `gp-0x69a4`'s real producer is a **live runtime 10-segment LERP
at `0x355C6` in `FUN_000352b4`** (the local *slope* of the curve, gated `|gp-0x4f60| ≤ 25600`) —
**1 writer / 3 readers: `0x355A4`, `0x3575A`, `0x3AB3A` (= the aggregator).**

⇒ **"r24 carries the entire lane" is a BELIEF resting on LEG 2 alone**, and the re-attribution of
**V42 / V61 / V62 to a single lane is CONTINGENT ON LEG 2.** It may well still be right.

### ★ The one indirect argument that LEG 2 holds — record it, it is what keeps the dose–response coherent
At `a = gp-0x69a4/1024 ≈ 1`, V67/V68's gate (gain_A **3072 → 512**, a **6.00× cut**) would put their
engaged **TOTAL** at **~0.94× stock** — essentially *on* stock. **Yet V67/V68 measured the best grind #1
result in the kit (median `e_18-22` engaged creep 109 vs stock's 879).** ⇒ **the empirical record argues
`a` is small.** [BELIEF — indirect, but it is the only thing making the dose–response self-consistent.]

## ✅ AND IT IS DIRECTLY MEASURABLE — V70 flies exactly the pair
`gp-0x6adc` is **r26's post-clamp mirror** (`st.h` @`0x3AD4E`, **0 readers / 1 writer** image-wide), and
r24/r26 share **ONE polarity load** — `ld.b -0x6752[gp],r14` @`0x3AB78`, reused at `0x3AB7E` (r26) and
`0x3AC3E` (r24) — so **they always carry the same sign.** Therefore `sign(gp-0x6adc)` vs
`sign(gp-0x6ada)` is a **matched pair**:

| observation | verdict |
|---|---|
| **bit4 pinned at 1 while bit3 toggles** | **r26 is ZERO** ⇒ LEG 2 holds, r24 carries the lane |
| **bit4 TRACKS bit3** | **r26 is LIVE** ⇒ LEG 2 falls, and V42/V61/V62 need re-attributing again |

**Non-vacuous in both directions. Resolvable on the next drive.**

## `0xC6444` — a CANDIDATE, not a recommendation
⚠ **Raising it is genuinely UNTESTED.** V42 tested it **downward** (512 → 0, FALSIFIED) — the same
*"tested downward ≠ tested upward"* distinction the V61 → V62 correction turned on
([[accord-rate-lane-is-the-damper-not-the-amplifier]]).
Blast radius: **1 reader / 0 writers, no float mirror, same CRC block #48 as `0xC6446`**, overflow
ceiling ≤ **6553**.
🛑 **V70 does not take it** — `a` is unmeasured, and V67/V68's control path is the measured best as it
stands. Do not propose it as a lever until `a` is bounded.

## Still true from the original note (byte-verified, unaffected by either leg)
- **Two-level scheduling.** Inner (`FUN_0003aa2c`, per tick): 4-point LERP on motor rate `gp-0x6ac0`.
  Outer (`FUN_0003ad74`): speed-class records via `gp-0x6a5e`, breakpoints `0xC6010` =
  [0, 640, 3200, 6400] = **0/10/50/100 km/h**. ⚠ Selection is **2-point between ADJACENT records only**,
  so ≥ 50.000 km/h reads only P2/P3.
- **gain_A (r26) is NOT mode-indexed** (`0xC6A68`/`0xC6A7C`/`0xC6A90`/`0xC6AA4`); **gain_B (r24) IS**,
  via `gp+0x63fd`.
- 🛑 **LERP record layout: `count` is u16 at +0**, then X[n], then Y[n].
- ★ **8 of 10 aggregator lanes are ZERO-GATES, not clamps.** Only r24/r26 use true saturating clamps
  (±8192 @`0x3AB82`/`0x3AC42`; aggregate ±10240 hard clip @`0x3ACE8`).

See [[accord-v69-flew-dose-response-non-monotone]], [[accord-v62-flashed-grinding-is-fixed]],
[[accord-aggregator-lane-mirrors-6ada-6adc]], [[accord-rate-lane-is-the-damper-not-the-amplifier]].
