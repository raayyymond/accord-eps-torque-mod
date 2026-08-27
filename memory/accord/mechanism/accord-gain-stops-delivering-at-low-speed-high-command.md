---
name: accord-gain-stops-delivering-at-low-speed-high-command
description: RETRACTED as a positive claim. Once speed is matched inside the bin, the 4x->6x gain step delivers 1.292 [0.925,1.673] below 15 mph against an ideal 1.500 - the CI CONTAINS 1.500, and the low/high contrast 0.711 [0.451,1.032] contains 1. The earlier "the gain stops delivering at low speed" was an artifact of unmatched speed distributions inside a wide bin. UNDERPOWERED, not refuted; closing it needs matched low-speed exposure.
metadata:
  node_type: memory
  type: reference
---

# 🛑🛑 RETRACTED AS A POSITIVE CLAIM — SPEED-MATCHING KILLS IT

★★★★★ **EVIDENCE for the retraction**, 2026-08-27, same day it was first written. The operator
asked: *"it feels like the max angular velocity has not scaled 6x."* **I told him twice that the data
agreed. Properly controlled, it does not — and it does not disagree either.**

## THE FINAL, PROPERLY-CONTROLLED NUMBERS
**2 mph speed cells** × `|cmd| >= 3072`, hands-off (D3), pooled only over cells where BOTH arms carry
≥ 1 s, route bootstrap resampling **both** arms. **Ideal = 1.500.**
```
  <=15 mph   1.292  [0.925, 1.673]   P(<1.500) = 0.860   P(<1.0) = 0.061
  >=15 mph   1.858  [1.387, 2.485]   P(<1.500) = 0.085
  CONTRAST   0.711  [0.451, 1.032]   P(<1)     = 0.963
```
⇒ **1.500 is INSIDE the low-speed interval. The contrast interval CONTAINS 1.** There is a
*suggestion* of a low-speed shortfall (point estimates 1.29 vs 1.86) but **nothing survives at 95 %.**

## 🛑 WHAT WENT WRONG — THREE ROUNDS OF CONTROLS, EACH ONE SHRINKING THE EFFECT
| round | design | low-speed ratio | verdict |
|---|---|---|---|
| 1 | no hands-off mask | 0.948 | **WRONG** — measured the DRIVER, not LKAS |
| 2 | hands-off, wide `<15 mph` bin | 1.030 [0.694, 1.499] | inflated by speed mismatch |
| 3 | + within-route ratio | (ratio 0.514) | same mismatch, hidden in a denominator |
| 4 | **+ 2 mph speed cells** | **1.292 [0.925, 1.673]** | **n.s.** |
⭐ **THE MECHANISM OF THE ERROR:** the two arms are not matched inside a wide bin — median speed
within `<15 mph` was **6.2 mph (4×) vs 8.3 mph (6×)**, and acceleration varies strongly across that
range. A bin wide enough to hold a speed gradient will manufacture a between-arm difference from a
pure exposure difference.
🛑 **RULE: for any cross-build contrast on this corpus, match speed in cells no wider than ~2 mph.
A `<15 mph` bin is NOT a speed control.** The routes differ enormously in low-speed exposure (r77 40 %
rail duty below 6 mph against r1e's 7.5 %).

## WHY IT IS **UNDERPOWERED**, NOT REFUTED
The 6× arm carries only **5–15 s per 2 mph cell** at `|cmd| >= 3072`. The interval
[0.925, 1.673] is 1.8× wide — it cannot distinguish "full delivery" from "a 30 % shortfall".
⇒ **Closing it needs matched low-speed exposure**: deliberate hands-off engaged segments at 2–15 mph
with large command, on both a 4× and a 6× build, on the same road. `docs/DRIVE-CARD-NEXT.md`
manoeuvre 2 is the right shape; it needs a large-command variant.

## ✅ WHAT SURVIVES FROM THAT SESSION, UNAFFECTED
1. **The ratchet/grind COMMAND GATE** — [[accord-ratchet-and-grind-are-command-gated-saturation]].
   That result is a **within-window band contrast with its own internal controls** (two control bands
   FALL while 6–9 Hz rises 3–4.7×). It never used a cross-arm comparison and **speed-matching does not
   touch it.**
2. **The hands-off lesson** — any cross-build torque or rate comparison at low speed is meaningless
   without a hands-off mask. Round 1 above is the proof.
3. **The E3 reconciliation** — a rate-vs-command test is structurally blind to a torque ceiling,
   because rate is an integral. E3's null on `0xC61BE` replicates on all six high-exposure routes and
   its decision was correct.
4. ❌ **NOT stick-slip** — stuck duty FALLS with command (0.609 → 0.009 below 15 mph).

---

# ⚠⚠ EVERYTHING BELOW IS THE **SUPERSEDED** ROUND-2/3 ANALYSIS — AUDIT TRAIL ONLY
Its numbers reproduce, but **its speed control is inadequate** and every cross-arm ratio in it is
inflated by the 6.2-vs-8.3 mph mismatch. **Read the retraction above; do not quote these figures.**

## THE INSTRUMENT (superseded)
**Angular acceleration in the commanded direction** — proportional to NET TORQUE at the instant,
before friction and damping have set a steady state. If the gain reaches the motor, it MUST scale.
Route-level p90 (the correct unit, per [[feedback-episodes-not-windows]]), **engaged AND hands-off**
(D3: rolling-median `|cs_tq|` over 0.5 s < 1200), bootstrapped over routes.
**Ladder read from the IMAGES, build tag read from each cache's `probe_build`:**
`0xC6CD0` = 891 stock (1×) · 3564 (4×, V77–V100) · 5346 (6×, V102+) · 7128 (8×, V101).
Well-powered arm = **4× (8 routes) vs 6× (6 routes)**; stock and 8× are one route each.

## THE RESULT (SUPERSEDED — speed-mismatched) — ideal is 1.500
```
  window                       4x->6x delivered      routes
  ALL speeds, |cmd| >= 3000    1.429 [1.134, 1.737]   8/6     <- the gain DOES reach the motor
  <15 mph,    |cmd| >= 2048    1.030 [0.694, 1.499]   8/6     <- it does NOT, here
  15-45 mph,  |cmd| >= 2048    1.814 [1.276, 2.521]   6/6     <- full delivery, even over
  RATIO-OF-RATIOS (low/high)   0.557 [0.359, 0.909]   P(<1) = 0.992
```
By command bin, `<15 mph`: 512–1k **1.494 [1.333,1.655]** · 1k–2k **1.533 [1.233,1.904]** ·
2k–3k **0.798** · 3k–4095 1.462 · RAIL **1.089 [0.749,1.593]**.
⇒ **At low command the gain delivers exactly as designed. It fails at low speed AND high command.**

## ⚠ SUPERSEDED — "CONFIRMED WITHIN-ROUTE": the within-route ratio carries the SAME speed mismatch
The result above is a BETWEEN-route comparison (different drives, different roads), which is its
weakest feature. The within-route version removes that: for **each route**, take the ratio of p90
acceleration at (<15 mph, `|cmd|≥2048`) to (15–45 mph, same command), then compare that ratio
between arms. Road, driving style and drive-to-drive variation cancel inside each route.
```
  4x  r77 2.333 | r78 1.000 | r79 5.000 | r7e 0.833 | r7f 2.500 | r85 1.500   mean 2.194
  6x  r96 1.000 | r9e 0.800 | ra4 1.200 | ra5 1.333 | ra6 1.667 | r1e 0.769   mean 1.128
  6x/4x of the WITHIN-ROUTE ratio = 0.514  [0.310, 0.944]   P(<1) = 0.985
```
⭐ **AND THE VARIANCE COLLAPSES.** The 4× arm spans **0.83–5.00**; the 6× arm spans **0.77–1.67**,
every route pinned near 1.0. **Being pinned to a common value across six independent drives is a
CEILING SIGNATURE** — it is what saturation looks like and what a road confound does not.
⇒ At 4×, low speed delivered **2.19×** the high-speed acceleration; at 6× only **1.13×**. The
low-speed advantage is absorbed when the gain goes to 6×.

## 🛑🛑 WHY V108's E3 NULL MISSED THIS — AND WHY E3 WAS STILL RIGHT
`build_v108_tva.py` E3 pre-registered: *"if achieved rate keeps rising to the top of the command
range, nothing in this lane saturates, the clip is idle"*, measured p90 **rate** top-vs-low-half and
got 3.89 / 3.12 / 2.91 / 2.62 / 2.14, every CI excluding 1.0 ⇒ **PULLED `0xC61BE`.**
⊕ **That null REPLICATES.** Re-run on the six routes with real low-speed exposure (E3 used `r1e`
alone, the least symptomatic low-speed route in the corpus — 7.5 % rail duty below 6 mph against
r77's 40 %), the bin-to-bin step ratios stay at 0.85–2.27 with **no collapse toward 1.0 at the top**
on any route. **There is no clamp being hit. E3's decision was correct.**
⇒ ⭐ **BUT RATE IS AN INTEGRAL.** A torque ceiling flattens **acceleration** while **rate keeps
rising**, because the capped torque is simply held for longer. **A rate-vs-command test is
structurally blind to a torque ceiling.** E3 was right about `0xC61BE` and could not have seen this.
🛑 **METHOD RULE: to test for a torque/authority ceiling, measure ACCELERATION, not rate.**

## ❌ REFUTED IN THE SAME PASS — IT IS NOT STICK-SLIP
Hypothesis: at low speed under a large command the rack sticks and breaks away, so "acceleration"
is set by the static→kinetic friction step rather than by applied torque. **Tested and refuted by
its own test.** Fraction of hands-off engaged time with `|rate| < 2.5 deg/s`, pooled over 14 routes:
```
  <15 mph   cmd <512  0.6090 | 0.5-1k 0.2094 | 1-2k 0.0791 | 2-3k 0.0272 | 3k+ 0.0089
  15-40     cmd <512  0.7446 | 0.5-1k 0.3426 | 1-2k 0.0937 | 2-3k 0.0290 | 3k+ 0.0171
```
**Stuck duty FALLS monotonically with command — 0.9 % at high command.** The wheel moves
essentially continuously. ⇒ **not stick-slip at the "wheel stops" level.** Recorded because it was
a plausible, attractive hypothesis that fit the operator's wording, and it is wrong.

## 🛑 THE CORRECTION THAT MADE THIS REAL — hands-on contamination
The **first** pass omitted the hands-off mask and returned "the gain scales NOWHERE" — ratio
0.948 [0.748, 1.182] at `|cmd| ≥ 3000`, `<15 mph`, and ~1.0 in **every** command bin with no knee.
**That was the driver, not the firmware.** At low speed the wheel is moved mostly by the operator's
own hands, and his torque swamped the LKAS contribution. Applying D3 flipped the low-command bins
from ~1.0 to ~1.50 and left the high-command bins near 1.0.
⭐ **THE LESSON: any cross-build torque or rate comparison at low speed is meaningless without a
hands-off mask.** The uncorrected version would have supported a much stronger and WRONG claim
("the 6× gain never reaches the motor"), which contradicts the measured fact that the gain
demonstrably causes the vibration ([[accord-the-8x-gain-is-the-carrier]]).

## ⚠ SUPERSEDED — SPEED OR RATE? (the interval that "excluded 1" no longer does)
Both gradients exist and they are confounded (low speed ⇒ more and faster steering):
```
  by VEHICLE SPEED   <10 mph 1.114 · 10-20 1.062 · 20-45 2.000 [1.316,2.764]
     contrast <10 / 20-45         0.557 [0.359, 0.909]   P(<1)=0.992   <- CI EXCLUDES 1
  by |STEERING RATE| <10 deg/s 1.621 · 10-30 1.537 · 30-80 0.895 · 80+ 1.019
     contrast 30-80 / <10        0.552 [0.304, 1.051]   P(<1)=0.964   <- CI includes 1
     contrast 80+   / <10        0.629 [0.336, 1.167]   P(<1)=0.931   <- CI includes 1
```
⇒ **[BELIEF] speed-scheduled rather than rate-indexed** — consistent with `0xC520C` (rate-indexed)
being struck. **Not proven**; the two splits cannot be fully separated on this corpus.

## WHAT IS EXCLUDED ALREADY
- **`0xC520C` cap table** — rate-indexed, first knot **222.8 °/s** vs a p90 of 100–140 °/s, and
  already STRUCK by its own author ([[accord-the-return-to-centre-crux-and-what-died-for-it]]).
- **The forward clamps `0xC61B2`/`0xC61B4`** — they **scale exactly with the gain**: 512 / 2048 /
  3072 / 4096 for 1× / 4× / 6× / 8×. Byte-verified across every image V96→V110.
- **openpilot's `STEER_MAX` = 4096** — a real, separate ceiling
  ([[accord-low-speed-rate-limit-is-openpilot-steer-max]]) but it caps the COMMAND, not the
  torque-per-command, so it cannot produce this. **Two ceilings stacking in the same regime.**

## STILL OPEN — the saturating element is NOT identified
Candidates, split by whether they are levers:
- **Firmware / possible lever:** the governor's vehicle-speed read (`0xC6316` ≈ 10 km/h); a shared
  base-assist + LKAS sum that Honda's own base curve already fills at low speed; the EME shaper.
- **Physics / NOT a lever:** motor current limit. Tyre scrub is highest at low speed, so the motor
  sits closest to max current; adding gain when already current-limited does nothing.
⇒ **The discriminator is a delivered-torque or motor-current channel**, which the corpus does not
carry cleanly across the 4×/6× builds (CAN 427 was repointed for probe use from V88 on).

Related: [[accord-ratchet-and-grind-are-command-gated-saturation]] ·
[[accord-4x-lkas-gain-is-the-frozen-variable]] · [[accord-fprime-compression-explains-v89-and-v97]]
