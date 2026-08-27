---
name: reference-accord-controls-killed-four-6to9hz-stories
description: "Four 6-9 Hz candidate stories died to their own controls on 2026-08-12: the assist-map operating point (flat across a 4x DC-bias range), Lever B 0xC6446 (cleared via pre-V74 builds that separate it from 0xD77DA, so V88's grinding fix need not be traded away), the 41-halfword cell search (0 hits at 6-9 Hz), and the manual hands-off coast test (structurally guaranteed to null)."
metadata:
  type: reference
---

# 🛑 FOUR 6–9 Hz STORIES KILLED BY THEIR OWN CONTROLS — do not re-propose these

All four died on 2026-08-12 in one session. A lever killed by a control cannot be revived by more
exposure or a bigger dose. Recorded because three of them are attractive enough to be re-proposed.

> 🛑🛑 **REGIME SCOPE, added 2026-08-12 — READ BEFORE CITING.** Every number in this file was
> measured **ENGAGED + HANDS-OFF**. The operator produces the symptom by **OVERRIDING** (engage,
> then turn against the command), and override is `steeringPressed == True` **by definition**, so
> this file characterises a regime **the symptom does not occur in**. The measurements are correct
> for what they measure — latent loop damping, hands-off — and they are **not** symptom
> measurements. See [[reference-accord-steeringpressed-mask-excludes-the-symptom-regime]].

## 1. THE ASSIST-MAP OPERATING POINT — REFUTED

The hypothesis: engaging puts a DC torque bias on the torsion bar (`P(gp-0x6bbe < 0)` **0.887
engaged vs 0.499 manual**), moving the operating point onto a higher-slope part of the assist curve
and raising the loop gain. It predicts `Re(Z)` scales with the DC bias **inside** the engaged arm.

Tested in four cells matched on speed **and** wheel rate, `|mean tq|` terciles spanning **34 → 148
counts (4×)**. 6–9 Hz `Re(Z)`:

```
static <1 °/s,  5-12 m/s   -2794 / -2709 / -2501
static <1 °/s, 12-22 m/s   -3167 / -2916 / -2876
MICRO 1-13,     5-12 m/s   -4388 / -3295 / -3620
MICRO 1-13,    12-22 m/s   -3922 / -3613 / -3830
```

**Flat, and if anything weakening with higher DC bias. Refuted.**

## 2. LEVER B (`0xC6446`) AS THE 6–9 Hz CULPRIT — CLEARED. ⭐ LOAD-BEARING FOR FUTURE BUILDS

The cross-build `Re(Z)` ledger steps at the **V84** boundary (V74–V83a mean −2902 vs V84–V92 mean
−3862 at 6–9 Hz). Two cells flipped there **together**, and no post-V74 build separates them:

```
0xC6446   512 -> 5244   Lever B (the LKAS-gated r24 rate lane) ARMED, gate 0x3AA96 c5 -> fb
0xD77DA   566 -> 0      the mode-26 base-assist damper zero-rate knot reverted to Honda
```

**Pre-V74 builds DO separate them** — read from the images: V67, V68 and **V71C** carry Lever B armed
with `0xD77DA` at stock 0; V65, V66, V69, V70, V71B, V72, V73 carry it disarmed, also at stock 0.
Scored, matched 5–22 m/s / |rate| < 13 °/s, 6–9 Hz:

| Lever B **ON** | Lever B **OFF** |
|---|---|
| V71C (r58) **−3169 [−3793, −2946]** | V69 (r4f) −3239 · V70 (r50) −3706 · V71B (r54) −2916 · V73 (r5a) −3028 |

**The ON arm sits in the middle of the OFF distribution. Lever B does not drive 6–9 Hz.**

⇒ 🛑 **V88's grinding fix does NOT have to be traded away to chase micro-ratcheting.** That is the
load-bearing consequence: the obvious V95 ("back Lever B off and see if micro-ratcheting improves")
is already answered, and the answer is no.

## 3. THE CELL SEARCH IS A NULL AT 6–9 Hz

Of the **41 calibration halfwords that vary across the 12 flown builds** with a scoreable ledger row
(regions `0xC4000-C5000`, `0xC6000-C7000`, `0xC9000-CC000`, `0xD6000-D8000`, cave and CRC trailers
excluded): **ZERO give a clean two-group separation at 6–9 Hz.** Also zero at 9–12 Hz.

Three separate at 12–16 **and** 18–22 Hz — `0xD780E`, `0xD7810`, `0xD7818`, which are knots of **one
LERP record** and therefore mutually confounded — at `p_exact` 0.0025–0.0040 against a Bonferroni bar
of **1.22e-3** for 41 tests. ⇒ **SUGGESTIVE, NOT SIGNIFICANT.** Do not build on them without a
single-variable flight.

⚠ Trap found while persisting this search: inverting the route→build map silently dropped V76 (whose
label is `V76-V38base`) and one of V89's two routes, cutting the search to 10 builds and turning the
6–9 Hz **null into 5 spurious "perfect" splits.** The script now uses an explicit map and prints
whatever it drops.

## 4. THE MANUAL HANDS-OFF COAST TEST — STRUCTURALLY GUARANTEED TO NULL AT 6–9 Hz

Proposed twice as the experiment that "gates the whole remaining search". It cannot work:

- **The premise was a census error.** `STATE.md` §A5 quoted **21.4 s** of manual hands-off in "the
  entire corpus". That is **route 77 alone**. The corpus holds **856.7 s** of manual hands-off
  moving, **491.1 s of it above 5 m/s**; route 66 alone has 275.0 s.
- **There is no excitation to find.** Hands off with LKAS off means the wheel does not move: median
  wheel rate **0.3 °/s** against 2.3–2.7 °/s engaged. 6–9 Hz coherence in the best-populated manual
  cell is **0.040 on 74 windows**, against a small-sample coherence bias of ≈ 1/n = **0.014**. The
  true coherence is near zero, so **more windows drive the estimate DOWN, not up.**
- The manoeuvre *does* return usable numbers at 9–26 Hz — but that band is already answered.

**Replacement, if the plant arm is wanted:** manual **hands-on impulse-and-release** (flick the rim,
let go, ring down), ~30 flicks per speed block at ~50 and ~80 km/h, ≈ 15 min. It excites at engaged
amplitude and yields ~60 ring-downs against the 1 the corpus has. 🛑 Score the decay from **150 ms
after** the last frame above 1200 counts, not from the `steeringPressed` edge — see
[[reference-accord-rez-anchored-on-car-and-its-floor]] §4. 🛑 Hands leave the rim on a moving car;
safety is the operator's judgement and a missing control beats an incident.

## REPRODUCE
`python rlog-tools/studies/impedance/v95_crossbuild_rez_ledger.py` (Lever B panel, cell search) ·
`python rlog-tools/studies/impedance/v95_rez_2x2.py` (the operating-point and coast-test arms).

Links: [[accord-v81-carries-neither-grind1-fix]] · [[accord-v88-flew-grinding-fixed-command-intact]]
· [[reference-accord-rez-anchored-on-car-and-its-floor]] ·
[[feedback-search-the-kit-before-naming-a-cause]] ·
[[feedback-run-the-control-before-the-measurement]] · [[accord-v64-null-is-on-the-gate]]
