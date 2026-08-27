---
name: accord-gain-stops-delivering-at-low-speed-high-command
description: Hands-off, the 4x->6x LKAS gain step delivers 1.43x [1.13,1.74] overall (ideal 1.500) - but only 1.03x [0.69,1.50] below 15 mph at high command, against 1.81x [1.28,2.52] at 15-45 mph. Ratio-of-ratios 0.557 [0.359,0.909]. The operator was right: there IS a structural limit that does not scale with the gain, and it is speed- and command-gated.
metadata:
  node_type: memory
  type: reference
---

# THE GAIN STOPS DELIVERING AT **LOW SPEED + HIGH COMMAND** — the operator was right

★★★★★ **EVIDENCE**, 2026-08-27. The operator, unprompted: *"I'm looking for a more structural
limitation on the steering angular velocity, one that does not scale with the 6x LKAS gain… it feels
like the max angular velocity has not scaled 6x."* **He was right, and the effect is specific.**

## THE INSTRUMENT
**Angular acceleration in the commanded direction** — proportional to NET TORQUE at the instant,
before friction and damping have set a steady state. If the gain reaches the motor, it MUST scale.
Route-level p90 (the correct unit, per [[feedback-episodes-not-windows]]), **engaged AND hands-off**
(D3: rolling-median `|cs_tq|` over 0.5 s < 1200), bootstrapped over routes.
**Ladder read from the IMAGES, build tag read from each cache's `probe_build`:**
`0xC6CD0` = 891 stock (1×) · 3564 (4×, V77–V100) · 5346 (6×, V102+) · 7128 (8×, V101).
Well-powered arm = **4× (8 routes) vs 6× (6 routes)**; stock and 8× are one route each.

## THE RESULT — ideal is 1.500
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

## ⭐⭐ CONFIRMED **WITHIN-ROUTE** — the road/driving confound cancelled
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

## SPEED OR RATE? — speed, on the only interval that excludes 1
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
