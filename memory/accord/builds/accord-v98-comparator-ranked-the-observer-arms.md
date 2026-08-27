---
name: accord-v98-comparator-ranked-the-observer-arms
description: "V98 flew as route 0x81 — the kit's first comparator probe ranked the observer residual's three arms. REQUEST is minor, MODEL and ACTUAL are COMPARABLE, and the \"arms are wildly unequal\" belief is refuted."
metadata: 
  node_type: memory
  type: reference
  originSessionId: fa9eb530-c732-4c40-8991-98e824e54a49
  modified: 2026-08-13T06:24:03.495Z
---

★★★★★ **V98 FLEW as route `0x81`** (3 segments, 2026-08-12), **fault-free**, and its comparator
answered the question V89 and V97 both died on. **Identity is single-frame proof:** `0x14A`
byte7[7:6] == **2** on **17,983 / 17,983 frames, duty 1.000000** (V96/V97 hard-wire 1; builds ≤ V91
give 0 ⇒ structurally excluded).

**Orchestrator-verified independently** by decoding the wire bits from `_scratch/cache/r81/r81.npz` — every
duty below reproduced exactly, and the engagement mask was cross-checked on the independent `0x18F`
byte4 bit3 channel (**agreement 0.999333**, 12 frames of 17,983; duties unchanged to 3 decimals).

## The result — duties over 6,591 ENGAGED frames [EVIDENCE]

```
iVar6 = gp-0x6bfe (MODEL) + gp-0x6bfa (REQUEST) - (gp-0x374c>>4) (ACTUAL)

(b6=0, b5=0)  0.5765     |MODEL| < |ACTUAL|  and  |REQUEST| < |ACTUAL|
(b6=1, b5=0)  0.4235     |MODEL| >= |ACTUAL| > |REQUEST|
(b6=0, b5=1)  0.0000
(b6=1, b5=1)  0.0000
```

**1. The LKAS REQUEST arm `gp-0x6bfa` is MINOR.** `b5` duty **0.0000 engaged (0 of 6,591)**. Not
structurally railed — it fires 38× in manual hands-off, only when ACTUAL is near zero.
⊕ Corroborated structurally: the REQUEST arm has **ZERO calibration cells** — its ±20000 bound is a
`movea` immediate at `0x273ac`/`0x273c4`, not a cal load — so there was never a cal-only lever there.

**2. MODEL and ACTUAL are COMPARABLE.** `b6` duty **0.4235 engaged** — a near coin-flip, the
pre-registered signature of *"both arms live, the residual is a genuine difference of two similar
numbers."*

🛑🛑 **THIS REFUTES THE STANDING `STATE.md` BELIEF** that *"the arms may be wildly unequal, so
whichever you move, the residual barely notices."* That was the one mechanism explaining **both** the
V89 and the V97 null, and **it is dead.**
⇒ **Neither null was a REACH failure. Both `0xC40D2` (K1, MODEL arm, V89) and `0xC63AC` (the IIR pole,
ACTUAL arm, V97) were CORRECTLY AIMED at live, comparable arms.** The nulls are about **DOSE or
DIRECTION**, not reach. That makes V89's flat result a *stronger* kill, and leaves V97's
UNINTERPRETABLE verdict intact (its problem was never reach — it was that a pole with **DC gain
1.000000 at every value** is invisible to every amplitude statistic the kit owns).

**3. `b3` closed a multi-session blocker: `sign(gp-0x6752) = −1`, CONSTANT NEGATIVE** over all 17,983
frames. ⇒ **`sign(gp-0x374c>>4) = −sign(sum6)`**, so **`b4 = 1 ⇔ the six-lane sum is POSITIVE`.**
⭐ **This may be the firmware side of the operator's own LKAS-vs-driver-torque frame flip** — see
[[accord-steering-sign-convention-confirmed]]. [BELIEF, cheap to close.]

**4. Engagement contrast on `b6`: 0.4235 engaged vs 0.8041 manual** (0.9756 in manual + hands-on),
and it **holds at matched speed** — 0.4246 vs 0.7273 in the 5–10 km/h band, so it is not a speed
artefact. ⇒ **Engaging LKAS is what drives the two arms into the near-cancelling regime**, and every
bad symptom the operator reports is LKAS-engaged-only. [Correspondence EVIDENCE; causal reading BELIEF.]

## Corroboration of the cancellation picture
Route 80 independently inverted the Stage-2 LERP and found **`|iVar6|` median ≈ 130** against terms
admitted to 2048 — **strong cancellation**, exactly what a `b6` near 0.5 predicts.
⇒ **The residual is dominated by whatever fails to cancel — phase mismatch, quantisation, or a
one-sided nonlinearity in one arm only.** The arms are mismatched in phase *by construction*: MODEL is
unfiltered, ACTUAL runs through the `0xC63AC` pole. **A one-sided nonlinearity in a near-cancelling
difference is a textbook stick-slip generator**, which is what grinding and micro-ratcheting are.

## Exposure and the matched pair
181.5 s / 3 segments / 17,982 rows @ 99.06 Hz. **Engaged 65.9 s (36.65 %) in 3 episodes, longest
29.8 s** — ~4× route 80's 17.2 s. Engaged v p50 **5.58 km/h**.
⭐ **seg1 = 76.3 % engaged (45.8 s), seg2 = 0.0 % engaged (59.9 s)** at overlapping creep speeds —
the operator's deliberate LKAS-off "this is how smooth it should be" demonstration. **This is the
within-route, matched-speed engaged/manual pair the kit has never had.** Ask for it on every drive.

## Instrument notes for the next build
- 🛑 **The `0x7FFF` plausibility latch has NEVER fired** — `427 == 1023` on **0 of 8,991** frames on
  route 81; **zero frames excluded** from `b6`. Fourth replication: never fired in **96,414 frames**
  across 7e / 7f / 80 / 81.
- ⚠ **`b5` came back at a RAIL (0.0000).** It decided something real, but a comparator rung that rails
  spends a bit to learn one bit. `b6` at 0.42 was the productive one.
- ⚠ **`cs_eng` is DEAD in the r81 cache** (duty 0.0000). Use `cc_lat` (latActive), cross-checked
  against `0x18F` byte4 bit3. Do not assume `cs_eng` works.
- 🛑 The ~50-build **"byte4[7:3] is always ODD" convention DOES NOT HOLD on V98** — `b3` is a
  measurand, so byte4 goes EVEN legitimately. Liveness moved to byte7. A scorer unaware of this pulls
  a working build.

Related: [[accord-steering-sign-convention-confirmed]] ·
[[accord-cbe74-dose-measured-inert-wrong-mode-record]] · [[accord-v89-built-plant-model-friction]] ·
[[accord-friction-polarity-more-assist]] · [[feedback-episodes-not-windows]]
