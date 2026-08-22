---
name: accord-v106-built-gp6b26-x3-mode-proof
description: "V106 BUILT: gp-0x6b26 (the acceleration/apparent-inertia damping term) raised to x3.0 stock on the two ENGAGED mode records only. 12 bytes, pure cal, 50/50 assertions. H(f=0)=0 EXACTLY so it cannot rate-limit a held 6x command. And it proves its own premise at zero cost - the carried b5 rung compares friction against the very cell being dosed, closing RULE 7 after four builds."
metadata:
  type: project
---

# ★★★★★ V106 BUILT — THE DAMPER, AND IT PROVES ITS OWN PREMISE

2026-08-22. `analysis-2020accord/build_v106_tva.py`, **50/50 assertions**, base = V105 (which flew as `a5`).
```
image  78528aa35b9ea2fa1ea990b2c8d41c7adc784fc17f0b481d66ddcfd3667cb65a
.rwd   e5ac6927a112a0cdf944971aebf7aa14efe6ad8597e17835bbc62d1589bfecbc
0xD7A5C  mode 26 (ENGAGED) Y  (-14745,-8601,-2949) -> (-29490,-17202,-5898)
0xD7A6C  mode 27 (ENGAGED) Y  (-14745,-8601,-2949) -> (-29490,-17202,-5898)   = x3.0 stock
```
**16 bytes differ from V105 (12 payload + 4 CRC). ZERO unattributed bytes vs stock.** One CRC trailer.

## WHY THIS LEVER
- 🛑 **The only lever in the kit with a SIGNED on-car precedent pointing this way.** V93/V94 LOWERED it and
  the operator aborted: *"made the stuttering and grinding worse, by a lot… not safe to drive."* The RAISE
  direction was never tested at 18–28 Hz — the "closed both directions" verdict rested on a
  **dose-VERIFICATION** check at 6–9 Hz. **FALSIFIED ≠ INERT ≠ UNTESTED.**
- **Damping removes a describing-function intersection; a notch relocates it** —
  [[accord-v105-relocated-the-mode-not-damped]] measured exactly that.
- **Reaches BOTH bands:** cascade gain **1.478 @ 7.79 Hz** (the ratchet line), **3.706 @ 21.73 Hz**.
- 🛑 **`H(f=0) = 0` EXACTLY.** The differencer `32·(1−z⁻¹)` is identically zero at DC for any `a1/a2/K`
  ⇒ **a held 6× command sees nothing from this term at any multiplier.** A proof, not a measurement, and
  it satisfies the operator's *"don't rate-limit me"* constraint by construction.

## ⭐ IT PROVES ITS OWN PREMISE — RULE 7 closed at zero cost
The carried cave rung **`b5` = ( |gp-0x6ae2| ≥ |gp-0x6b26| )** = FRICTION vs INERTIA. Operand B at
**`0xC4B70` = `da94` = disp `-0x6b26`** — the exact cell dosed (asserted in the builder).
```
b5 engaged duty COLLAPSES  => the car IS reading modes 26/27 engaged. Dose arrived.
b5 engaged duty UNCHANGED  => it is NOT => V91/V92's mode-record suspicion CONFIRMED,
                              this build is inert, and V107 doses mode 24 instead.
```
Baseline on `a5`: **0.2533 pooled, 0.4019 engaged <16 km/h. MANUAL is the built-in control.**
🛑 The mode record has **NEVER been directly telemetered** — V93 was built as a discriminator (via
dose-ratio inference) and never flew, and `accord-cbe74-dose-measured-inert-wrong-mode-record` names it as
the suspect for V91/V92. **The operator asked "why don't we put telemetry on it?" and that question found
a four-build hole.**

## 🛑 26/27 ONLY — the family has FOUR members
```
slot0 0xCBED4 -> 0xD6A64  Y@0xD6A6C  mode 24  MANUAL              stock, NEVER DOSED
slot1 0xCBED8 -> 0xD7A44  Y@0xD7A4C  mode 25  ROLE UNCONFIRMED    stock, NEVER DOSED
slot2 0xCBEDC -> 0xD7A54  Y@0xD7A5C  mode 26  ENGAGED  x1.5 since V96  <- DOSED
slot3 0xCBEE0 -> 0xD7A64  Y@0xD7A6C  mode 27  ENGAGED  x1.5 since V96  <- DOSED
```
Each record base occurs **exactly once** as an LE32 literal image-wide. `build_v100_tva.py`'s
`DOSE_FAMILY_Y` lists **three** (`build_v105_tva.py` already had four). **Mode 24 is MANUAL** ⇒ dosing it
is inert for an engagement-conditional symptom and changes manual/LKAS-off feel instead. **Mode 25's role
is unconfirmed** (shares 24's selector `gp-0x67f6 = 0`, differs only in `gp-0x67e2`, untraced) ⇒ the
V69/V70 trap class. Both left alone, and both dosed arms move by the same factor.

## SAFETY
🛑 **`0xC407E` NOT TOUCHED, still 511.** `FUN_00036c12` clamps `gp-0x6b26` to ±511 **before** the RULE-11
monitor `FUN_00036d74` compares it (trips above 512) ⇒ **structurally untrippable at ANY multiplier.**
V73 raised a *different* cell's clamp past its own trip and **V74/V75 both hard-faulted mid-drive.**
**Intact by construction, not by care.**
**Int32 overflow** on the `mid × 0x111` product: threshold `503342400/29490` = **17,068** vs a corpus max
of **5,320** — 3.2× margin, zero frames near it.

## ⚠ THE HIGH-RATE COST IS REAL, NOT ZERO — the orchestrator's own retraction
Measured off the 427 wire (r77/r78), `|gp-0x6b26|` **peaks at 40–100 °/s and COLLAPSES above 100**:
```
|rate| deg/s     0-5    5-15   15-40   40-100   100-200   200-400
p99             62.4   113.6   147.2    181.6      72.7      92.1
MAX            292.8   302.4   302.4    318.4     190.4     104.0
duty >= 511    0.000   0.000   0.000    0.000     0.000     0.000
```
MAX at 200–400 °/s is **104**, not the 543 predicted from a rate-monotone model (5.2× over). ⇒ **the raise
ARRIVES in full at high rate — a real added opposition the operator will feel in fast turns.** By the same
token **it arrives in scenario 2 too**, so V106 CAN reach his grind #2. **Clipping, if any, appears in
SCENARIO 1 (~1 % at k=3) — 26× more than in scenario 2.** The mirror of the original worry.

## ⭐ AND THE ×1.5 MAY NEVER HAVE BEEN IN FORCE
r78 (V91, ×1.5) vs r77 (V90, ×1.0) is an unread dose-response on this exact cell: **observed ratio ~0.7–1.1
against an expected 1.50.** [BELIEF — cross-drive, fails its own split-half null.] **If so, V106 is not a
×2 step from today but the FIRST REAL DOSE this cell has ever received engaged**, and the operator should
expect a larger change than "double the damping" implies. **`b5` settles it.**

Drive card: `docs/HANDOFF-2026-08-22-v106-the-damper-and-the-one-mode.md` §5, nine numbered questions.
Related: [[accord-v105-relocated-the-mode-not-damped]] · [[accord-three-grinds-are-one-frequency]] ·
[[accord-c407e-is-the-fault-interlock-c63a0-exonerated]] · [[reference-accord-car-is-tvca4-mode-24-26]]
